import { useState, useEffect, useCallback } from 'react'
import { listExpenses } from './api'
import type { Expense } from './api'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'

function App() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [fetchError, setFetchError] = useState<string | null>(null)

  const fetchExpenses = useCallback(async () => {
    try {
      const data = await listExpenses()
      setExpenses(data)
      setFetchError(null)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load expenses')
    }
  }, [])

  useEffect(() => {
    fetchExpenses()
  }, [fetchExpenses])

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
      <h1>Finance Tracker</h1>
      <h2>Add Expense</h2>
      <ExpenseForm onExpenseAdded={fetchExpenses} />
      <h2>Expenses</h2>
      {fetchError && <p style={{ color: 'red' }}>{fetchError}</p>}
      <ExpenseList expenses={expenses} />
    </div>
  )
}

export default App
