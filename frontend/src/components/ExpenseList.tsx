import type { Expense } from '../api'

interface Props {
  expenses: Expense[]
}

export function ExpenseList({ expenses }: Props) {
  if (expenses.length === 0) {
    return <p>No expenses yet.</p>
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Category</th>
          <th>Amount</th>
          <th>Currency</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {expenses.map((e) => (
          <tr key={e.id}>
            <td>{e.date}</td>
            <td>{e.category}</td>
            <td>{e.amount}</td>
            <td>{e.currency}</td>
            <td>{e.description ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
