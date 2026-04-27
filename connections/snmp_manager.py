"""SNMP adapter for network and OOB assets."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


def _normalize_protocol(value: str | None) -> str:
    return str(value or "").strip().lower().replace("-", "").replace("_", "")


class SNMPExecutor:
    def _auth_protocol(self, module, value: str | None):
        normalized = _normalize_protocol(value)
        return {
            "": module.usmNoAuthProtocol,
            "none": module.usmNoAuthProtocol,
            "noauth": module.usmNoAuthProtocol,
            "md5": module.usmHMACMD5AuthProtocol,
            "sha": module.usmHMACSHAAuthProtocol,
            "sha1": module.usmHMACSHAAuthProtocol,
            "sha224": module.usmHMAC128SHA224AuthProtocol,
            "sha256": module.usmHMAC192SHA256AuthProtocol,
            "sha384": module.usmHMAC256SHA384AuthProtocol,
            "sha512": module.usmHMAC384SHA512AuthProtocol,
        }.get(normalized)

    def _priv_protocol(self, module, value: str | None):
        normalized = _normalize_protocol(value)
        return {
            "": module.usmNoPrivProtocol,
            "none": module.usmNoPrivProtocol,
            "nopriv": module.usmNoPrivProtocol,
            "des": module.usmDESPrivProtocol,
            "3des": module.usm3DESEDEPrivProtocol,
            "aes": module.usmAesCfb128Protocol,
            "aes128": module.usmAesCfb128Protocol,
            "aes192": module.usmAesCfb192Protocol,
            "aes256": module.usmAesCfb256Protocol,
        }.get(normalized)

    def get(
        self,
        *,
        host: str,
        port: int,
        oid: str,
        extra_args: dict | None = None,
    ) -> dict:
        extra_args = extra_args or {}
        version = str(extra_args.get("snmp_version") or "v2c").lower()
        if version in {"2", "2c"}:
            version = "v2c"
        if version in {"3"}:
            version = "v3"

        try:
            from pysnmp.hlapi import asyncio as snmp_asyncio
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pysnmp 依赖，请先安装 requirements.txt 中的 pysnmp 后再连接 SNMP 资产。",
            }

        async def _run():
            get_cmd = getattr(snmp_asyncio, "get_cmd", None)
            if get_cmd is None:
                get_cmd = getattr(snmp_asyncio, "getCmd")
            target = await snmp_asyncio.UdpTransportTarget.create(
                (host, int(port)), timeout=5, retries=1
            )
            if version == "v2c":
                credentials = snmp_asyncio.CommunityData(
                    extra_args.get("community_string") or "public",
                    mpModel=1,
                )
            elif version == "v3":
                username = (
                    extra_args.get("v3_username")
                    or extra_args.get("v3_auth_user")
                    or extra_args.get("security_name")
                    or extra_args.get("username")
                    or extra_args.get("user")
                )
                if not username:
                    return None, None, None, None, "SNMPv3 缺少 security username/v3_username。"
                auth_protocol = self._auth_protocol(snmp_asyncio, extra_args.get("v3_auth_protocol"))
                priv_protocol = self._priv_protocol(snmp_asyncio, extra_args.get("v3_priv_protocol"))
                if auth_protocol is None:
                    return None, None, None, None, f"不支持的 SNMPv3 auth 协议: {extra_args.get('v3_auth_protocol')}"
                if priv_protocol is None:
                    return None, None, None, None, f"不支持的 SNMPv3 priv 协议: {extra_args.get('v3_priv_protocol')}"
                credentials = snmp_asyncio.UsmUserData(
                    username,
                    authKey=extra_args.get("v3_auth_pass") or None,
                    privKey=extra_args.get("v3_priv_pass") or None,
                    authProtocol=auth_protocol,
                    privProtocol=priv_protocol,
                )
            else:
                return None, None, None, None, f"不支持的 SNMP 版本: {version}"

            result = await get_cmd(
                snmp_asyncio.SnmpEngine(),
                credentials,
                target,
                snmp_asyncio.ContextData(),
                snmp_asyncio.ObjectType(snmp_asyncio.ObjectIdentity(oid)),
            )
            return (*result, None)

        try:
            error_indication, error_status, error_index, var_binds, local_error = asyncio.run(_run())
            if local_error:
                return {"success": False, "error": local_error}
            if error_indication:
                return {"success": False, "error": str(error_indication)}
            if error_status:
                return {"success": False, "error": f"{error_status.prettyPrint()} at {error_index}"}
            return {
                "success": True,
                "data": [
                    {"oid": str(name), "value": value.prettyPrint()} for name, value in var_binds
                ],
            }
        except Exception as e:
            logger.error("SNMP get failed: %s", e)
            return {"success": False, "error": str(e)}


snmp_executor = SNMPExecutor()
