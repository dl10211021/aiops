from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.session import (
    custom_slash_command_deleted_response_kwargs,
    custom_slash_command_saved_response_kwargs,
    custom_slash_command_updated_response_kwargs,
    custom_slash_commands_response_kwargs,
)
from api.schemas import ResponseModel, SlashCommandPayload
from core.session_commands import (
    SessionCommandError,
    list_custom_slash_command_records,
    remove_custom_slash_command_record,
    save_custom_slash_command_record,
)


router = APIRouter()


@router.get("/commands/custom", response_model=ResponseModel)
async def list_custom_slash_commands():
    """列出用户自定义快捷命令。"""
    commands = await list_custom_slash_command_records()
    return ResponseModel(**custom_slash_commands_response_kwargs(commands))


@router.post("/commands/custom", response_model=ResponseModel)
async def create_custom_slash_command(req: SlashCommandPayload):
    """创建用户自定义快捷命令。"""
    command = await save_custom_slash_command_record(
        req.model_dump(),
    )
    return ResponseModel(**custom_slash_command_saved_response_kwargs(command))


@router.put("/commands/custom/{command_id}", response_model=ResponseModel)
async def update_custom_slash_command(command_id: str, req: SlashCommandPayload):
    """更新用户自定义快捷命令。"""
    command = await save_custom_slash_command_record(
        req.model_dump(),
        command_id,
    )
    return ResponseModel(**custom_slash_command_updated_response_kwargs(command))


@router.delete("/commands/custom/{command_id}", response_model=ResponseModel)
async def delete_custom_slash_command(command_id: str):
    """删除用户自定义快捷命令。"""
    try:
        await remove_custom_slash_command_record(command_id)
    except SessionCommandError as exc:
        raise_http_error(exc)
    return ResponseModel(**custom_slash_command_deleted_response_kwargs())
