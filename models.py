from sqlalchemy import String, Integer, Column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Phone(Base):
    __tablename__ = "smartphone"
    id = Column(Integer,primary_key=True)
    nama_smartphone = Column(String)
    ram = Column(Integer)
    storage = Column(Integer)
    chipset = Column(String)
    layar = Column(String)
    harga = Column(Integer)
    baterai = Column(Integer)

    def __repr__(self):
        return f"Phone(nama_smartphone={self.nama_smartphone!r}, ram={self.ram!r}, storage={self.storage!r}, chipset={self.chipset!r}, layar={self.layar!r},  harga={self.harga!r}, b   aterai={self.baterai!r})"
