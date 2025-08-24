from sqlalchemy import create_engine, Column, String, Text, ForeignKey, Integer, TIMESTAMP, func, ARRAY
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class MedusaProduct(Base):
    __tablename__ = "product"

    id = Column(String, primary_key=True)
    title = Column(Text)
    brand = Column(Text)
    thumbnail = Column(Text)
    images = Column(Text)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    farfetch_data = relationship(
        "FarfetchProduct", back_populates="medusa_product")
    lyst_data = relationship("LystProduct", back_populates="medusa_product")
    italist_data = relationship(
        "ItalistProduct", back_populates="medusa_product")
    leam_data = relationship("LeamProduct", back_populates="medusa_product")
    modesens_data = relationship(
        "ModesensProduct", back_populates="medusa_product")
    reversible_data = relationship(
        "ReversibleProduct", back_populates="medusa_product")
    selfridge_data = relationship(
        "SelfridgeProduct", back_populates="medusa_product")


class FarfetchProduct(Base):
    __tablename__ = "farfetch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="farfetch_data")


class LystProduct(Base):
    __tablename__ = "lyst"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="lyst_data")


class ItalistProduct(Base):
    __tablename__ = "italist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="italist_data")


class LeamProduct(Base):
    __tablename__ = "leam"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="leam_data")


class ModesensProduct(Base):
    __tablename__ = "modesens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="modesens_data")


class ReversibleProduct(Base):
    __tablename__ = "reversible"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="reversible_data")


class SelfridgeProduct(Base):
    __tablename__ = "selfridge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medusa_id = Column(String, ForeignKey("product.id", ondelete="CASCADE"))
    product_url = Column(Text)
    brand = Column(Text)
    product_name = Column(Text)
    product_details = Column(Text)
    category = Column(Text)
    thumbnail = Column(Text)
    image_urls = Column(Text)
    original_price = Column(Text)
    sale_price = Column(Text)
    discount = Column(Text)
    price_aed = Column(Text)
    price_usd = Column(Text)
    price_gbp = Column(Text)
    price_eur = Column(Text)
    size_and_fit = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    medusa_product = relationship(
        "MedusaProduct", back_populates="selfridge_data")
