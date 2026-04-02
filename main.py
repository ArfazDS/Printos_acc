from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

active_sessions = {}

def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in active_sessions:
        return None
    user_id = active_sessions[session_token]
    return db.query(models.User).filter(models.User.id == user_id).first()

def require_auth(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
    return user

def require_admin(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return user

def require_employee(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return user

def get_unread_enquiries_count(db: Session):
    return db.query(models.Enquiry).filter(models.Enquiry.status == "unread").count()

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin = models.User(username="admin", password="password", role="admin")
        db.add(admin)
    
    # Data Seeding for Printo Products
    if db.query(models.Product).count() == 0:
        seed_products = [
            models.Product(name="Standard Business Cards", category="Business Cards", description="Premium 300gsm double-sided printing.", price=250.0),
            models.Product(name="Custom Corporate Hoodie", category="Apparel", description="High-quality winter hoodies with company logo.", price=1200.0),
            models.Product(name="Employee Joining Kit", category="Corporate Gifting", description="Notebook, Pen, Coffee Mug, and Welcome Letter.", price=2500.0),
            models.Product(name="Personalized Ceramic Mug", category="Drinkware", description="Standard 330ml mug printing.", price=350.0),
            models.Product(name="Large Flex Banner", category="Signage", description="Outdoor flex printing 6x3 ft.", price=850.0)
        ]
        db.add_all(seed_products)
        
    db.commit()

# --- AUTH & INDEX ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/employee", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username, models.User.password == password).first()
    if not user:
        return RedirectResponse(url="/?error=1", status_code=status.HTTP_303_SEE_OTHER)
    
    import uuid
    token = str(uuid.uuid4())
    active_sessions[token] = user.id
    
    url = "/admin/dashboard" if user.role == "admin" else "/employee"
    res = RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    res.set_cookie(key="session_token", value=token)
    return res

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token in active_sessions:
        del active_sessions[token]
    res = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    res.delete_cookie(key="session_token")
    return res

# --- STOREFRONT ---

@app.get("/store", response_class=HTMLResponse)
async def store(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    user = get_current_user(request, db)
    return templates.TemplateResponse("store.html", {"request": request, "products": products, "user": user})

@app.post("/store/enquire")
async def store_enquire(product_id: int = Form(...), customer_name: str = Form(...), customer_phone: str = Form(...), db: Session = Depends(get_db)):
    enq = models.Enquiry(product_id=product_id, customer_name=customer_name, customer_phone=customer_phone)
    db.add(enq)
    db.commit()
    return RedirectResponse(url="/store?enquiry_success=1", status_code=status.HTTP_303_SEE_OTHER)

# --- ADMIN ROUTES ---

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    # Chart logic
    txs = db.query(models.Transaction).order_by(models.Transaction.date).all()
    
    chart_labels = []
    income_data = []
    expense_data = []
    cumulative_profit = []
    current_profit = 0
    
    # Simple grouping just for demonstration (Vyapar aggregates by day/month ideally)
    for t in txs:
        date_str = str(t.date)
        if date_str not in chart_labels:
            chart_labels.append(date_str)
            income_data.append(0)
            expense_data.append(0)
            
        idx = chart_labels.index(date_str)
        if t.type == "income":
            income_data[idx] += t.amount
            current_profit += t.amount
        else:
            expense_data[idx] += t.amount
            current_profit -= t.amount
            
    for _ in chart_labels:
        # Just drawing a simplified overall running profit for the line graph
        cumulative_profit.append(current_profit) # Just keeping flat for simplicity right now unless we compute per day. Let's just pass data.
    
    total_income = sum([t.amount for t in txs if t.type == "income"])
    total_expense = sum([t.amount for t in txs if t.type == "expense"])
    
    # Enquiries
    recent_enquiries = db.query(models.Enquiry).order_by(models.Enquiry.date.desc()).limit(10).all()
    unread_c = get_unread_enquiries_count(db)
    employees = db.query(models.User).filter(models.User.role == "employee").all()
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user,
        "unread_count": unread_c,
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": total_income - total_expense,
        "chart_labels": chart_labels,
        "income_data": income_data,
        "expense_data": expense_data,
        "recent_enquiries": recent_enquiries,
        "employees": employees
    })

@app.post("/admin/assign_task")
async def assign_task(request: Request, enquiry_id: int = Form(...), employee_id: int = Form(...), db: Session = Depends(get_db)):
    require_admin(request, db)
    enq = db.query(models.Enquiry).filter(models.Enquiry.id == enquiry_id).first()
    if enq:
        assignment = models.TaskAssignment(enquiry_id=enquiry_id, employee_id=employee_id)
        db.add(assignment)
        enq.status = "assigned"
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/resolve_enquiry")
async def admin_resolve_enquiry(request: Request, enquiry_id: int = Form(...), db: Session = Depends(get_db)):
    require_admin(request, db)
    enq = db.query(models.Enquiry).filter(models.Enquiry.id == enquiry_id).first()
    if enq:
        enq.status = "resolved"
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    products = db.query(models.Product).all()
    unread_c = get_unread_enquiries_count(db)
    return templates.TemplateResponse("admin_products.html", {
        "request": request, "user": user, "products": products, "unread_count": unread_c
    })

@app.post("/admin/products/add")
async def admin_add_product(request: Request, name: str = Form(...), category: str = Form("General"), description: str = Form(""), price: float = Form(0.0), db: Session = Depends(get_db)):
    require_admin(request, db)
    p = models.Product(name=name, category=category, description=description, price=price)
    db.add(p)
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/accounting", response_class=HTMLResponse)
async def admin_accounting(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    txs = db.query(models.Transaction).order_by(models.Transaction.date.desc()).all()
    unread_c = get_unread_enquiries_count(db)
    return templates.TemplateResponse("admin_accounting.html", {
        "request": request, "user": user, "transactions": txs, "unread_count": unread_c
    })

@app.post("/admin/accounting/add")
async def admin_add_transaction(request: Request, t_type: str = Form(...), amount: float = Form(...), t_date: date = Form(...), description: str = Form(...), gst_type: str = Form("None"), gst_amount: float = Form(0.0), db: Session = Depends(get_db)):
    require_admin(request, db)
    t = models.Transaction(type=t_type, amount=amount, date=t_date, description=description, gst_type=gst_type, gst_amount=gst_amount)
    db.add(t)
    db.commit()
    return RedirectResponse(url="/admin/accounting", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/employees", response_class=HTMLResponse)
async def admin_employees(request: Request, employee_id: int = None, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    
    employees = db.query(models.User).filter(models.User.role == "employee").all()
    
    work_query = db.query(models.WorkEntry)
    task_query = db.query(models.TaskAssignment)
    
    if employee_id:
        work_query = work_query.filter(models.WorkEntry.employee_id == employee_id)
        task_query = task_query.filter(models.TaskAssignment.employee_id == employee_id)
        
    work_entries = work_query.order_by(models.WorkEntry.date.desc()).all()
    assigned_tasks = task_query.order_by(models.TaskAssignment.assigned_date.desc()).all()
    
    unread_c = get_unread_enquiries_count(db)
    return templates.TemplateResponse("admin_employees.html", {
        "request": request, 
        "user": user, 
        "employees": employees, 
        "work_entries": work_entries, 
        "assigned_tasks": assigned_tasks,
        "selected_emp_id": employee_id,
        "unread_count": unread_c
    })

@app.post("/admin/create_employee")
async def create_employee(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    require_admin(request, db)
    existing = db.query(models.User).filter(models.User.username == username).first()
    if not existing:
        new_emp = models.User(username=username, password=password, role="employee")
        db.add(new_emp)
        db.commit()
    return RedirectResponse(url="/admin/employees", status_code=status.HTTP_303_SEE_OTHER)

# --- EMPLOYEE ROUTES ---

@app.get("/employee", response_class=HTMLResponse)
async def employee_dashboard(request: Request, filter_date: str = None, db: Session = Depends(get_db)):
    user = require_employee(request, db)
    
    query = db.query(models.WorkEntry).filter(models.WorkEntry.employee_id == user.id)
    if filter_date:
        query = query.filter(models.WorkEntry.date == filter_date)
    
    entries = query.order_by(models.WorkEntry.date.desc()).all()
    total_val = sum([e.value for e in entries])
    
    # Fetch active tasks assigned to this employee
    tasks = db.query(models.TaskAssignment).filter(models.TaskAssignment.employee_id == user.id).order_by(models.TaskAssignment.assigned_date.desc()).all()
    
    return templates.TemplateResponse("employee.html", {
        "request": request,
        "user": user,
        "entries": entries,
        "total_val": total_val,
        "filter_date": filter_date,
        "tasks": tasks
    })

@app.post("/employee/update_task")
async def employee_update_task(request: Request, assignment_id: int = Form(...), status: str = Form(...), notes: str = Form(""), db: Session = Depends(get_db)):
    user = require_employee(request, db)
    task = db.query(models.TaskAssignment).filter(models.TaskAssignment.id == assignment_id, models.TaskAssignment.employee_id == user.id).first()
    if task:
        task.status = status
        task.employee_notes = notes
        if status == "Completed":
            # Optional: Move the parent enquiry to resolved
            task.enquiry.status = "resolved"
        db.commit()
    return RedirectResponse(url="/employee", status_code=303)

@app.post("/employee/add_work")
async def add_work(request: Request, work_date: date = Form(...), description: str = Form(...), value: float = Form(...), db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        
    entry = models.WorkEntry(employee_id=user.id, date=work_date, description=description, value=value)
    db.add(entry)
    db.commit()
    return RedirectResponse(url="/employee", status_code=status.HTTP_303_SEE_OTHER)
