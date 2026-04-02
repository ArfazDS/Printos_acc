from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)  # In a real app, hash this!
    role = Column(String)      # 'admin' or 'employee'

    work_entries = relationship("WorkEntry", back_populates="employee")

class WorkEntry(Base):
    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    description = Column(String)
    value = Column(Float, default=0.0)

    employee = relationship("User", back_populates="work_entries")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="General")
    description = Column(Text, nullable=True)
    price = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    image_url = Column(String, nullable=True)

    enquiries = relationship("Enquiry", back_populates="product")

class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    customer_name = Column(String)
    customer_phone = Column(String)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="unread") # unread, resolved

    product = relationship("Product", back_populates="enquiries")
    assignments = relationship("TaskAssignment", back_populates="enquiry")

class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    enquiry_id = Column(Integer, ForeignKey("enquiries.id"))
    employee_id = Column(Integer, ForeignKey("users.id"))
    assigned_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Pending") # Pending, In Progress, Completed
    employee_notes = Column(Text, nullable=True)

    enquiry = relationship("Enquiry", back_populates="assignments")
    employee = relationship("User")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String) # 'income' or 'expense'
    amount = Column(Float, default=0.0)
    category = Column(String, nullable=True)
    gst_type = Column(String, nullable=True) # CGST, SGST, IGST, None
    gst_amount = Column(Float, default=0.0)
    date = Column(Date, index=True)
    description = Column(String)
