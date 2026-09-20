const form = document.querySelector('#search-form');
const input = document.querySelector('#term');
const button = document.querySelector('#search-button');
const message = document.querySelector('#message');
const cards = document.querySelector('#cards');
const count = document.querySelector('#result-count');

async function search(term) {
  button.disabled = true;
  count.textContent = 'RUNNING';
  message.textContent = 'Running a parameterized query…';
  cards.replaceChildren();
  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({term}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Search failed.');
    count.textContent = `${data.count} RESULT${data.count === 1 ? '' : 'S'}`;
    message.textContent = data.count
      ? 'The term was searched as text. It did not change the SQL statement.'
      : 'No matching product. The input stayed a literal search value.';
    for (const result of data.results) {
      const card = document.createElement('article');
      const category = document.createElement('small');
      const title = document.createElement('h4');
      const description = document.createElement('p');
      category.textContent = result.category;
      title.textContent = result.name;
      description.textContent = result.description;
      card.append(category, title, description);
      cards.append(card);
    }
  } catch (error) {
    count.textContent = 'ERROR';
    message.textContent = error.message === 'Failed to fetch' ? 'Server unavailable. Try again shortly.' : error.message;
  } finally {
    button.disabled = false;
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  search(input.value);
});

document.querySelectorAll('[data-example]').forEach(example => {
  example.addEventListener('click', () => {
    input.value = example.dataset.example;
    search(input.value);
  });
});
