export interface Expense {
  id: string
  amount: string
  currency: string
  category: string
  date: string
  description: string | null
}

export interface CreateExpensePayload {
  amount: string
  currency: string
  category: string
  date: string
  description?: string
}

export async function createExpense(payload: CreateExpensePayload): Promise<Expense> {
  const response = await fetch('/expenses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(`Failed to create expense: ${response.status}`)
  }
  return response.json()
}

export async function listExpenses(): Promise<Expense[]> {
  const response = await fetch('/expenses')
  if (!response.ok) {
    throw new Error(`Failed to fetch expenses: ${response.status}`)
  }
  return response.json()
}
