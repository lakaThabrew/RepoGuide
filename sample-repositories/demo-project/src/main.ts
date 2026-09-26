import express from 'express'
import { userService } from './services/userService'

const app = express()
const PORT = process.env.PORT || 3001

app.use(express.json())

// List all users
app.get('/users', (_req, res) => {
  res.json(userService.list())
})

// Get user by ID
app.get('/users/:id', (req, res) => {
  const user = userService.getById(req.params.id)
  if (!user) {
    res.status(404).json({ error: 'User not found' })
    return
  }
  res.json(user)
})

// Create user
app.post('/users', (req, res) => {
  const { name, email } = req.body as { name?: string; email?: string }
  if (!name || !email) {
    res.status(400).json({ error: 'name and email are required' })
    return
  }
  const user = userService.create({ name, email })
  res.status(201).json(user)
})

// Update user
app.put('/users/:id', (req, res) => {
  const updated = userService.update(req.params.id, req.body)
  if (!updated) {
    res.status(404).json({ error: 'User not found' })
    return
  }
  res.json(updated)
})

// Delete user
app.delete('/users/:id', (req, res) => {
  const removed = userService.remove(req.params.id)
  if (!removed) {
    res.status(404).json({ error: 'User not found' })
    return
  }
  res.status(204).send()
})

app.listen(PORT, () => {
  console.log(`demo-project API listening on http://localhost:${PORT}`)
})

export default app
