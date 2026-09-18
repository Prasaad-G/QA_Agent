const express = require('express');
const TodoManager = require('./todo');

const app = express();
app.use(express.json());

const manager = new TodoManager();

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/api/todos', (req, res) => {
  res.json(manager.getTodos());
});

app.post('/api/todos', (req, res) => {
  try {
    const todo = manager.addTodo(req.body.title);
    res.status(201).json(todo);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.patch('/api/todos/:id/toggle', (req, res) => {
  try {
    const todo = manager.toggleTodo(parseInt(req.params.id, 10));
    res.json(todo);
  } catch (err) {
    res.status(404).json({ error: err.message });
  }
});

app.delete('/api/todos/:id', (req, res) => {
  const success = manager.deleteTodo(parseInt(req.params.id, 10));
  if (!success) {
    return res.status(404).json({ error: 'Not found' });
  }
  res.json({ success: true });
});

module.exports = app;

