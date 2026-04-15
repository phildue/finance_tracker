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

export async function deleteExpense(id: string): Promise<void> {
  const response = await fetch(`/expenses/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`Failed to delete expense: ${response.status}`)
  }
}

export async function deleteExpenses(ids: string[]): Promise<void> {
  const response = await fetch('/expenses/bulk', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
  if (!response.ok) {
    throw new Error(`Failed to delete expenses: ${response.status}`)
  }
}

export async function deleteAllExpenses(): Promise<void> {
  const response = await fetch('/expenses', { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`Failed to delete all expenses: ${response.status}`)
  }
}

export async function getVersion(): Promise<string> {
  const response = await fetch('/version')
  if (!response.ok) {
    return 'unknown'
  }
  const data = await response.json()
  return data.version
}
