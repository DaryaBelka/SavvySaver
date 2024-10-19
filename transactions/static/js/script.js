function getStarted() {
  window.location.href = 'transactions/';
}

document.addEventListener('DOMContentLoaded', () => {
  const navItems = document.querySelectorAll('.nav li');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(i => i.classList.remove('active')); // remove the active class from all menu elements and add it to the clicked element
      item.classList.add('active');

      window.location.href = item.querySelector('a').href;
    });
  });
});
