import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Float
from app.core.database import Base


class ProjectRisk(Base):
    """SQLAlchemy model for project risk register."""

    __tablename__ = "project_risks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    risk_code = Column(String(30), nullable=False)  # e.g. RSK-01
    title = Column(String(255), nullable=False)
    # Categories: technical, schedule, budget, scope, resource, operational, security
    category = Column(String(50), nullable=False, default="technical")
    description = Column(Text, nullable=False)

    likelihood = Column(Integer, nullable=False, default=3)  # 1-5 scale
    impact = Column(Integer, nullable=False, default=3)      # 1-5 scale
    risk_score = Column(Integer, nullable=False, default=9)  # likelihood * impact (1-25)
    # Levels: low (1-4), medium (5-9), high (10-15), critical (16-25)
    risk_level = Column(String(20), nullable=False, default="medium")

    supporting_evidence = Column(Text, nullable=True)
    mitigation_strategy = Column(Text, nullable=True)
    risk_owner = Column(String(255), nullable=True)
    # Statuses: identified, mitigated, accepted, closed
    status = Column(String(30), nullable=False, default="identified")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class FeasibilityAssessment(Base):
    """SQLAlchemy model for 7-dimension feasibility assessment."""

    __tablename__ = "feasibility_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)

    # Status: feasible, caution, infeasible
    overall_status = Column(String(30), nullable=False, default="caution")
    overall_score = Column(Float, nullable=False, default=70.0)  # 0 - 100

    # JSON of dimensions: schedule, budget, skill, technical, scope, data_completeness, operational
    dimensions_json = Column(Text, nullable=False)
    limitations_json = Column(Text, nullable=True)
    summary = Column(Text, nullable=False)

    assessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
