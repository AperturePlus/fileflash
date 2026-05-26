from enum import Enum


class BaseStrEnum(str, Enum):
	"""Base enum for string-backed values used by DB and APIs."""

	def __str__(self) -> str:
		return self.value


class UploadStatus(BaseStrEnum):
	UPLOADING = "uploading"
	ACTIVE = "active"
	DELETED = "deleted"
	FAILED = "failed"


class FolderStatus(BaseStrEnum):
	ACTIVE = "active"
	DELETED = "deleted"


class FileStatus(BaseStrEnum):
	ACTIVE = "active"
	DELETED = "deleted"


class UploadMode(BaseStrEnum):
	SINGLE = "single"
	MULTIPART = "multipart"


class UploadTaskStatus(BaseStrEnum):
	INIT = "init"
	UPLOADING = "uploading"
	COMPLETED = "completed"
	ABORTED = "aborted"
	FAILED = "failed"


class UploadPartStatus(BaseStrEnum):
	PENDING = "pending"
	UPLOADED = "uploaded"
	FAILED = "failed"


class UserStatus(BaseStrEnum):
	PENDING_VERIFICATION = "pending_verification"
	ACTIVE = "active"
	LOCKED = "locked"
	DISABLED = "disabled"


class UserRole(BaseStrEnum):
	USER = "USER"
	ADMIN = "ADMIN"


class UiLanguage(BaseStrEnum):
	ZH_CN = "zh-CN"
	EN_US = "en-US"


class FolderType(BaseStrEnum):
	NORMAL = "normal"
	ROOT = "root"
	SYSTEM = "system"


class ShareStatus(BaseStrEnum):
	ACTIVE = "active"
	EXPIRED = "expired"
	REVOKED = "revoked"
	DELETED = "deleted"


class ShareMemberStatus(BaseStrEnum):
	PENDING = "pending"
	ACCEPTED = "accepted"
	REJECTED = "rejected"
	REVOKED = "revoked"


class FavoriteItemType(BaseStrEnum):
	FILE = "file"
	FOLDER = "folder"


class ViewMode(BaseStrEnum):
	LIST = "list"
	GRID = "grid"


class SortBy(BaseStrEnum):
	NAME = "name"
	SIZE = "size"
	CREATED_AT = "created_at"
	UPDATED_AT = "updated_at"
	LAST_ACCESSED_AT = "last_accessed_at"


class SortDirection(BaseStrEnum):
	ASC = "asc"
	DESC = "desc"


class PreviewStatus(BaseStrEnum):
	PENDING = "pending"
	READY = "ready"
	FAILED = "failed"


class ScanResult(BaseStrEnum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    BLOCKED = "blocked"
    FAILED = "failed"


class AgentExecutionPolicy(BaseStrEnum):
    PLAN_ONLY = "planOnly"
    CONFIRM = "confirm"
    AUTOPILOT = "autopilot"


class AgentMemoryScope(BaseStrEnum):
    GLOBAL = "global"
    WORKSPACE = "workspace"
    SESSION = "session"


class AgentMemoryKind(BaseStrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    FEEDBACK = "feedback"
    REFERENCE = "reference"


class AgentSkillVisibility(BaseStrEnum):
    GLOBAL = "global"
    PRIVATE = "private"


class AgentMcpVisibility(BaseStrEnum):
    SYSTEM = "system"
    PRIVATE = "private"


class AgentInboxRole(BaseStrEnum):
    AGENT = "agent"
    USER = "user"


class AgentInboxKind(BaseStrEnum):
    ASK = "ask"
    REPLY = "reply"
    CONTROL_PAUSE = "control.pause"
    CONTROL_RESUME = "control.resume"
    CONTROL_APPROVE = "control.approve"
    CONTROL_DENY = "control.deny"
    CONTROL_SKIP = "control.skip"
    CONTROL_CANCEL = "control.cancel"


class AgentInboxStatus(BaseStrEnum):
    WAITING = "waiting"
    ANSWERED = "answered"
    TIMED_OUT = "timed_out"
    DROPPED = "dropped"


__all__ = [
	"BaseStrEnum",
	"UploadStatus",
	"FolderStatus",
	"FileStatus",
	"UploadMode",
	"UploadTaskStatus",
	"UploadPartStatus",
	"UserRole",
	"UserStatus",
	"UiLanguage",
	"FolderType",
	"ShareStatus",
	"ShareMemberStatus",
	"FavoriteItemType",
	"ViewMode",
	"SortBy",
    "SortDirection",
    "PreviewStatus",
    "ScanResult",
    "AgentExecutionPolicy",
    "AgentMemoryScope",
    "AgentMemoryKind",
    "AgentSkillVisibility",
    "AgentMcpVisibility",
    "AgentInboxRole",
    "AgentInboxKind",
    "AgentInboxStatus",
]

