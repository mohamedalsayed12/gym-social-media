from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(200), server_default=text("''"))

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="community", cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "community_members"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    community: Mapped["Community"] = relationship(back_populates="memberships")
