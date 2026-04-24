import os
import lancedb
import logging
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class KnowledgeBaseManager:
    def __init__(self, db_path="opscore_lancedb"):
        self.db_path = db_path
        self.kb_dir = "knowledge_base"
        os.makedirs(self.kb_dir, exist_ok=True)
        self.ldb = lancedb.connect(self.db_path)

    def _get_embedding_model(self):
        try:
            from core.agent import EMBEDDING_MODEL
            return EMBEDDING_MODEL
        except ImportError:
            return "models/gemini-embedding-001"

    def _get_embedding_dim(self):
        try:
            from core.agent import EMBEDDING_DIM
            return EMBEDDING_DIM
        except ImportError:
            return 3072

    async def ingest_document(self, file_path, client):
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
            
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=500)
        splits = text_splitter.split_documents(docs)
        
        table_name = "knowledge_base"
        
        # 准备数据插入
        data = []
        for i, split in enumerate(splits):
            try:
                # 调用 Gemini 向量模型
                emb_res = await client.embeddings.create(input=split.page_content, model=self._get_embedding_model())
                vector = emb_res.data[0].embedding
                data.append({
                    "id": f"{os.path.basename(file_path)}_{i}",
                    "source": os.path.basename(file_path),
                    "content": split.page_content,
                    "vector": vector
                })
            except Exception as e:
                logger.error(f"Embedding failed for chunk {i}: {e}")
                
        if not data:
             return {"status": "error", "message": "文档内容提取或向量化失败"}

        # 创建或打开表
        if table_name not in self.ldb.table_names():
            # 定义 schema
            import pyarrow as pa
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("source", pa.string()),
                pa.field("content", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self._get_embedding_dim())) # Configurable embedding dimension
            ])
            tbl = self.ldb.create_table(table_name, schema=schema)
        else:
            tbl = self.ldb.open_table(table_name)
            
        tbl.add(data)
        return {"status": "success", "message": f"成功将 {os.path.basename(file_path)} 注入知识库，共 {len(data)} 个知识块。"}

    async def search(self, query, client, limit=10):
        """根据问题检索最相关的知识片段"""
        if "knowledge_base" not in self.ldb.table_names():
            return "当前企业知识库为空，无参考文档。"
            
        try:
            emb_res = await client.embeddings.create(input=query, model=self._get_embedding_model())
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
        if "knowledge_base" not in self.ldb.table_names():
            return []
        try:
            tbl = self.ldb.open_table("knowledge_base")
            # 取出所有 source 字段去重
            df = tbl.search().select(["source"]).limit(10000).to_pandas()
            if len(df) == 0:
                return []
            sources = df["source"].unique().tolist()
            return sources
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return []

    async def delete_document(self, filename: str):
        """删除指定文档的所有块"""
        if "knowledge_base" not in self.ldb.table_names():
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

kb_manager = KnowledgeBaseManager()
