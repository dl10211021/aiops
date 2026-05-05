import os
import lancedb
import logging
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.lancedb_utils import ensure_lancedb_table, lancedb_table_names

logger = logging.getLogger(__name__)

class KnowledgeBaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv("OPSCORE_LANCEDB_PATH") or "opscore_lancedb"
        self.kb_dir = "knowledge_base"
        os.makedirs(self.kb_dir, exist_ok=True)
        self.ldb = lancedb.connect(self.db_path)

    def _get_embedding_model(self):
        try:
            from core.embedding_config import EMBEDDING_MODEL
            return EMBEDDING_MODEL
        except ImportError:
            return ""

    def _get_embedding_dim(self):
        try:
            from core.embedding_config import EMBEDDING_DIM
            return EMBEDDING_DIM
        except ImportError:
            return 3072

    async def ingest_document(self, file_path, client, embedding_model: str | None = None):
        """解析文档、分块、向量化并存入 LanceDB"""
        if not os.path.exists(file_path):
            return {"status": "error", "message": "文件不存在"}
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext in [".docx", ".doc"]:
            loader = Docx2txtLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")
            
        try:
            docs = loader.load()
        except Exception as e:
            logger.error("文档内容提取失败: %s", e)
            return {"status": "error", "message": f"文档内容提取失败：{e}"}
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=500)
        splits = text_splitter.split_documents(docs)
        if not splits:
            return {"status": "error", "message": "未提取到可用于检索索引的文本内容"}
        
        table_name = "knowledge_base"
        
        # 准备数据插入
        data = []
        embedding_errors = []
        for i, split in enumerate(splits):
            try:
                emb_res = await client.embeddings.create(
                    input=split.page_content,
                    model=embedding_model or self._get_embedding_model(),
                )
                vector = emb_res.data[0].embedding
                data.append({
                    "id": f"{os.path.basename(file_path)}_{i}",
                    "source": os.path.basename(file_path),
                    "content": split.page_content,
                    "vector": vector
                })
            except Exception as e:
                embedding_errors.append(str(e))
                logger.error(f"Embedding failed for chunk {i}: {e}")
                
        if not data:
            if embedding_errors:
                return {"status": "error", "message": f"向量模型调用失败：{embedding_errors[-1]}"}
            return {"status": "error", "message": "文档内容提取或向量化失败"}

        # 创建或打开表
        if table_name not in lancedb_table_names(self.ldb):
            # 定义 schema
            import pyarrow as pa
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("source", pa.string()),
                pa.field("content", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self._get_embedding_dim())) # Configurable embedding dimension
            ])
            tbl = ensure_lancedb_table(self.ldb, table_name, schema)
        else:
            tbl = self.ldb.open_table(table_name)
            
        tbl.add(data)
        return {"status": "success", "message": f"成功将 {os.path.basename(file_path)} 注入知识库，共 {len(data)} 个知识块。"}

    async def search(self, query, client, embedding_model: str | None = None, limit=10):
        """根据问题检索最相关的知识片段"""
        if "knowledge_base" not in lancedb_table_names(self.ldb):
            return "当前企业知识库为空，无参考文档。"
            
        try:
            emb_res = await client.embeddings.create(
                input=query,
                model=embedding_model or self._get_embedding_model(),
            )
            query_vector = emb_res.data[0].embedding
            
            tbl = self.ldb.open_table("knowledge_base")
            results = tbl.search(query_vector).limit(limit).to_pandas()
            
            if len(results) == 0:
                return "知识库中未找到相关内容。"
                
            context = "【企业知识库参考】：\n"
            for i in range(len(results)):
                row = results.iloc[i]
                context += f"- 来源: {row['source']}\n  内容: {row['content']}\n\n"
            return context
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return f"检索失败: {str(e)}"

    async def list_documents(self):
        """列出所有已注入的文档"""
        if "knowledge_base" not in lancedb_table_names(self.ldb):
            return []
        try:
            tbl = self.ldb.open_table("knowledge_base")
            # 取出所有 source 字段去重。不要使用无查询向量的 search()，
            # 新版 LanceDB 会等待有效查询并导致 /knowledge/list 卡住。
            try:
                df = tbl.to_pandas()
            except AttributeError:
                df = tbl.head(10000).to_pandas()
            if len(df) == 0:
                return []
            if "source" not in df.columns:
                return []
            sources = df["source"].unique().tolist()
            return sources
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return []

    async def delete_document(self, filename: str):
        """删除指定文档的所有块"""
        if "knowledge_base" not in lancedb_table_names(self.ldb):
            return {"status": "error", "message": "知识库为空"}
        try:
            tbl = self.ldb.open_table("knowledge_base")
            
            # 防御 SQL 注入 (LanceDB Delete Filter)
            safe_filename = filename.replace("'", "''")
            tbl.delete(f"source = '{safe_filename}'")
            
            # 同时删除物理文件
            # 防御目录穿越
            safe_file_basename = os.path.basename(filename)
            file_path = os.path.join(self.kb_dir, safe_file_basename)
            if os.path.exists(file_path):
                os.remove(file_path)
                
            # 执行整理和清理碎片
            try:
                tbl.cleanup_old_versions()
                tbl.compact_files()
                logger.info("LanceDB knowledge_base 整理和清理完成。")
            except Exception as e:
                logger.warning(f"LanceDB 整理报错: {e}")
                
            return {"status": "success", "message": f"已成功从知识库中移除 {filename}"}
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return {"status": "error", "message": str(e)}

class LazyKnowledgeBaseManager:
    """Delay LanceDB connection until a vector operation really needs it."""

    def __init__(self):
        self._manager = None

    @property
    def db_path(self):
        if self._manager is not None:
            return self._manager.db_path
        return os.getenv("OPSCORE_LANCEDB_PATH") or "opscore_lancedb"

    @property
    def kb_dir(self):
        if self._manager is not None:
            return self._manager.kb_dir
        return "knowledge_base"

    def materialize(self):
        if self._manager is None:
            self._manager = KnowledgeBaseManager(self.db_path)
        return self._manager

    def __getattr__(self, name):
        return getattr(self.materialize(), name)


kb_manager = LazyKnowledgeBaseManager()
