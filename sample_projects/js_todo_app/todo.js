class TodoManager {
  constructor() {
    this.todos = [];
    this.nextId = 1;
  }

  addTodo(title) {
    if (!title || typeof title !== 'string' || title.trim() === '') {
      throw new Error('Title must be a non-empty string');
    }
    const todo = {
      id: this.nextId++,
      title: title.trim(),
      completed: false,
      createdAt: new Date().toISOString()
    };
    this.todos.push(todo);
    return todo;
  }

  getTodos() {
    return [...this.todos];
  }

  toggleTodo(id) {
    const todo = this.todos.find(t => t.id === id);
    if (!todo) {
      throw new Error(`Todo with id ${id} not found`);
    }
    todo.completed = !todo.completed;
    return todo;
  }

  deleteTodo(id) {
    const index = this.todos.findIndex(t => t.id === id);
    if (index === -1) {
      return false;
    }
    this.todos.splice(index, 1);
    return true;
  }
}

module.exports = TodoManager;

