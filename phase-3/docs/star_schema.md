# PulseIQ star schema

Grain, keys and joins come from the dataset README and were checked against the real warehouse columns. `dim_employee` is SCD Type 2 (one row per employee version), so facts join on `employee_key`.

## 1a. Payroll star

![Payroll star](<fact_payroll star schema.png>)

```mermaid
erDiagram
    DIM_EMPLOYEE ||--o{ FACT_PAYROLL : employee_key
    DIM_DATE ||--o{ FACT_PAYROLL : date_key
    DIM_DEPARTMENT ||--o{ FACT_PAYROLL : department_id
    DIM_ROLE ||--o{ FACT_PAYROLL : role_id
```

## 1b. Attendance and leave stars

![Attendance and leave stars](Employee Attendance and Leave Data Model.png)

```mermaid
erDiagram
    DIM_EMPLOYEE ||--o{ FACT_ATTENDANCE_MONTHLY : employee_key
    DIM_DATE ||--o{ FACT_ATTENDANCE_MONTHLY : date_key
    DIM_DEPARTMENT ||--o{ FACT_ATTENDANCE_MONTHLY : department_id
    DIM_EMPLOYEE ||--o{ FACT_LEAVE : employee_key
    DIM_LEAVE_TYPE ||--o{ FACT_LEAVE : leave_type_code
    DIM_DATE ||--o{ FACT_LEAVE : start_end_date_key
```

## 1c. Headcount and attrition risk stars

```mermaid
erDiagram
    DIM_DEPARTMENT ||--o{ FACT_HEADCOUNT_MONTHLY : department_id
    DIM_DATE ||--o{ FACT_HEADCOUNT_MONTHLY : date_key
    DIM_EMPLOYEE ||--o{ FACT_ATTRITION_RISK : employee_key
    DIM_DEPARTMENT ||--o{ FACT_ATTRITION_RISK : department_id
    DIM_DATE ||--o{ FACT_ATTRITION_RISK : as_of_date_key
```

## 2a. Ledger, invoice and payment stars

```mermaid
erDiagram
    DIM_ACCOUNT ||--o{ FACT_LEDGER : account_code
    DIM_DEPARTMENT ||--o{ FACT_LEDGER : cost_center_department_id
    DIM_DATE ||--o{ FACT_LEDGER : date_key
    DIM_CLIENT ||--o{ FACT_INVOICE : client_id
    DIM_ACCOUNT ||--o{ FACT_INVOICE : service_line_account
    DIM_DATE ||--o{ FACT_INVOICE : invoice_date_key
    DIM_DATE ||--o{ FACT_INVOICE_PAYMENT : payment_date_key
```

## 2b. Expense star

```mermaid
erDiagram
    DIM_VENDOR ||--o{ FACT_EXPENSE : vendor_id
    DIM_ACCOUNT ||--o{ FACT_EXPENSE : category_account
    DIM_DEPARTMENT ||--o{ FACT_EXPENSE : department_id
    DIM_DATE ||--o{ FACT_EXPENSE : expense_date_key
```

## 2c. Task, anomaly and forecast stars

```mermaid
erDiagram
    DIM_TEAM ||--o{ FACT_TASK : team_id
    DIM_SPRINT ||--o{ FACT_TASK : sprint_id
    DIM_EMPLOYEE ||--o{ FACT_TASK : assignee_employee_id
    DIM_EMPLOYEE ||--o{ FACT_ANOMALY : employee_id
    DIM_DATE ||--o{ FACT_FORECAST : forecast_month_key
    DIM_DEPARTMENT ||--o{ FACT_FORECAST : department_id
    DIM_DATE ||--o{ FACT_FORECAST : date_key
```