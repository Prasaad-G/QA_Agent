"""FastAPI Calculator Web API."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from calculator import Calculator

app = FastAPI(title="Calculator Service", version="1.0.0")
calc = Calculator()


class CalculationRequest(BaseModel):
    a: float = Field(..., description="First operand")
    b: float = Field(..., description="Second operand")


class PowerRequest(BaseModel):
    base: float
    exponent: float


@app.get("/")
def read_root():
    return {"status": "online", "service": "Calculator Service"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/calculate/add")
def add_numbers(req: CalculationRequest):
    result = calc.add(req.a, req.b)
    return {"operation": "add", "result": result}


@app.post("/calculate/subtract")
def subtract_numbers(req: CalculationRequest):
    result = calc.subtract(req.a, req.b)
    return {"operation": "subtract", "result": result}


@app.post("/calculate/multiply")
def multiply_numbers(req: CalculationRequest):
    result = calc.multiply(req.a, req.b)
    return {"operation": "multiply", "result": result}


@app.post("/calculate/divide")
def divide_numbers(req: CalculationRequest):
    try:
        result = calc.divide(req.a, req.b)
        return {"operation": "divide", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/calculate/power")
def power_numbers(req: PowerRequest):
    result = calc.power(req.base, req.exponent)
    return {"operation": "power", "result": result}


@app.get("/history")
def get_history():
    return {"history": calc.get_history()}


@app.delete("/history")
def clear_history():
    calc.clear_history()
    return {"message": "History cleared"}

