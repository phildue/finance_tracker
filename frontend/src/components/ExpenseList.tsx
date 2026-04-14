import { useState } from 'react'
import type { Expense } from '../api'
import { deleteExpenses, deleteAllExpenses } from '../api'

interface Props {
  expenses: Expense[]
  onDeleted: () => void
  onDeleteError: (msg: string) => void
}

export function ExpenseList({ expenses, onDeleted, onDeleteError }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  if (expenses.length === 0) {
    return <p>No expenses yet.</p>
  }

  const allSelected = selectedIds.size === expenses.length
  const someSelected = selectedIds.size > 0 && !allSelected

  function toggleAll() {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(expenses.map((e) => e.id)))
    }
  }

  function toggleRow(id: string) {
    const next = new Set(selectedIds)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setSelectedIds(next)
  }

  async function handleDeleteSelected() {
    if (!window.confirm(`Delete ${selectedIds.size} selected ${selectedIds.size === 1 ? 'entry' : 'entries'}?`)) return
    try {
      await deleteExpenses([...selectedIds])
      setSelectedIds(new Set())
      onDeleted()
    } catch (err) {
      onDeleteError(err instanceof Error ? err.message : 'Failed to delete entries')
    }
  }

  async function handleDeleteAll() {
    if (!window.confirm('Delete all entries?')) return
    try {
      await deleteAllExpenses()
      setSelectedIds(new Set())
      onDeleted()
    } catch (err) {
      onDeleteError(err instanceof Error ? err.message : 'Failed to delete all entries')
    }
  }

  return (
    <>
      {selectedIds.size > 0 && (
        <div>
          <span>{selectedIds.size} selected</span>
          {' '}
          <button onClick={handleDeleteSelected}>Delete selected</button>
          {' '}
          <button onClick={handleDeleteAll}>Delete all</button>
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => { if (el) el.indeterminate = someSelected }}
                onChange={toggleAll}
              />
            </th>
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
              <td>
                <input
                  type="checkbox"
                  checked={selectedIds.has(e.id)}
                  onChange={() => toggleRow(e.id)}
                />
              </td>
              <td>{e.date}</td>
              <td>{e.category}</td>
              <td>{e.amount}</td>
              <td>{e.currency}</td>
              <td>{e.description ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
