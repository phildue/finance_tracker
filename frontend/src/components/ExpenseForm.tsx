import { useState } from 'react'
import type { FormEvent } from 'react'
import { createExpense } from '../api'

interface Props {
  onExpenseAdded: () => void
}

export function ExpenseForm({ onExpenseAdded }: Props) {
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [category, setCategory] = useState('')
  const [date, setDate] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createExpense({
        amount,
        currency,
        category,
        date,
        description: description || undefined,
      })
      setAmount('')
      setCurrency('EUR')
      setCategory('')
      setDate('')
      setDescription('')
      onExpenseAdded()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="amount">Amount</label>
        <input
          id="amount"
          type="number"
          step="0.01"
          min="0.01"
          required
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="currency">Currency</label>
        <input
          id="currency"
          type="text"
          required
          value={currency}
          onChange={(e) => setCurrency(e.target.value.toUpperCase())}
        />
      </div>
      <div>
        <label htmlFor="category">Category</label>
        <input
          id="category"
          type="text"
          required
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="date">Date</label>
        <input
          id="date"
          type="date"
          required
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="description">Description (optional)</label>
        <input
          id="description"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button type="submit">Add Expense</button>
    </form>
  )
}
