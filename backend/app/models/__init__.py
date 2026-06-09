from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so they register with Base.metadata
from app.models.tool import Tool  # noqa: E402, F401
from app.models.rating import UserRating  # noqa: E402, F401
from app.models.analytics import SearchLog, ToolView, UserSession, EmailCapture  # noqa: E402, F401
from app.models.prompt import PromptVersion, PromptEvalResult  # noqa: E402, F401
from app.models.conversation import ConversationTurn  # noqa: E402, F401
from app.models.rating_event import RatingEvent  # noqa: E402, F401
from app.models.admin_token import AdminToken  # noqa: E402, F401
from app.models.tool_save import ToolSave  # noqa: E402, F401
from app.models.pulse_survey import PulseSurveyResponse  # noqa: E402, F401
