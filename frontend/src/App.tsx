import { useState, useEffect, useCallback } from 'react'
import { listExpenses } from './api'
import type { Expense } from './api'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'

function App() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const fetchExpenses = useCallback(async () => {
    setDeleteError(null)
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
      {deleteError && <p style={{ color: 'red' }}>{deleteError}</p>}
      <ExpenseList
        expenses={expenses}
        onDeleted={fetchExpenses}
        onDeleteError={setDeleteError}
      />
    </div>
  )
}

export default App
