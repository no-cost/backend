from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from settings import Settings
from utils import random_id


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(
        String(length=4),  # 35^4 = 1500625 possible site combinations
        primary_key=True,
        unique=True,
        nullable=False,
        default=random_id,
    )

    # Account
    admin_email: Mapped[str] = mapped_column(String(length=255), nullable=False)
    admin_password: Mapped[str] = mapped_column(
        String(length=72), nullable=False  # bcrypt
    )

    # Config
    site_type: Mapped[str] = mapped_column(String(length=30), nullable=False)
    hostname: Mapped[str] = mapped_column(String(length=255), nullable=True)
    chroot_dir: Mapped[str] = mapped_column(String(length=255), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(nullable=True)

    # Removal
    removal_reason: Mapped[str] = mapped_column(String(length=255), nullable=True)
    removed_at: Mapped[datetime] = mapped_column(nullable=True)
    removed_ip: Mapped[str] = mapped_column(String(length=45), nullable=True)

    # IPs
    created_ip: Mapped[str] = mapped_column(String(length=45), nullable=True)
    last_login_ip: Mapped[str] = mapped_column(String(length=45), nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(nullable=True)

    # Misc
    donated_amount: Mapped[float] = mapped_column(nullable=True)
    """Donations are per site, in EUR"""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )

    def is_installed(self) -> bool:
        """Returns whether the site was installed successfully"""
        return self.installed_at is not None

    def get_parent_domain(self) -> str:
        """Returns the parent domain of the site's hostname"""
        last_2_parts = self.hostname.split(".")[-2:]
        return ".".join(last_2_parts)

    def is_donor(self) -> bool:
        """Returns whether the site admin has donated"""
        return self.donated_amount is not None and self.donated_amount > 0

    def has_perks(self) -> bool:
        """Returns whether the site admin has donated enough to have perks (such as the footer removed)"""
        return (
            self.donated_amount is not None
            and self.donated_amount >= Settings.PERKS_DONATION_AMOUNT
        )
