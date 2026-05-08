from sqlalchemy import Column, Integer, String, Text

from app.storage.database import Base


class PrescriptionRecordDB(Base):

    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    record_id = Column(String, unique=True)
    source_file = Column(String)
    method = Column(String)

    extracted_json = Column(Text)
    review_json = Column(Text)
    metadata_json = Column(Text)
    