/* ═══════════════════════════════════════════════════════════════════
   SWIRL — Order Modal & WhatsApp Integration
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // Config: Enter the salesman's WhatsApp number here (with country code, no +, spaces, or dashes)
  // e.g. "919999999999" (91 is country code for India, followed by 10-digit number)
  var SALESMAN_NUMBER = "919891470611";

  // DOM elements
  var modal = document.getElementById('order-modal');
  var closeBtn = document.getElementById('modal-close-btn');
  var form = document.getElementById('order-form');

  // Find all CTA and Order buttons on the page
  var orderButtons = [
    document.getElementById('cta-button'),
    document.querySelector('.nav-cta'),
  ];

  // Also catch any other button pointing to order
  var allButtons = document.querySelectorAll('a, button');
  allButtons.forEach(function (btn) {
    var text = (btn.textContent || '').toLowerCase();
    var href = btn.getAttribute('href');
    if (text.indexOf('order now') !== -1 || text.indexOf('taste the swirl') !== -1 || href === '#cta') {
      if (orderButtons.indexOf(btn) === -1) {
        orderButtons.push(btn);
      }
    }
  });

  // Open modal handler
  function openModal(e) {
    if (e) e.preventDefault();
    modal.classList.add('open');
    document.body.style.overflow = 'hidden'; // Lock scroll
  }

  // Close modal handler
  function closeModal() {
    modal.classList.remove('open');
    document.body.style.overflow = ''; // Unlock scroll
  }

  // Bind open click event to all buttons
  orderButtons.forEach(function (btn) {
    if (btn) {
      btn.addEventListener('click', openModal);
      // Remove anchor jump behavior if it was an anchor
      if (btn.tagName === 'A') {
        btn.setAttribute('href', 'javascript:void(0);');
      }
    }
  });

  // Bind close click events
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  // Close when clicking outside modal content
  window.addEventListener('click', function (e) {
    if (e.target === modal) {
      closeModal();
    }
  });

  // Form submit handler
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Get values
      var name = document.getElementById('order-name').value.trim();
      var phone = document.getElementById('order-phone').value.trim();
      var product = document.getElementById('order-product').value;
      var details = document.getElementById('order-details').value.trim();
      var address = document.getElementById('order-address').value.trim();
      var date = document.getElementById('order-date').value;
      var time = document.getElementById('order-time').value;

      // Construct beautifully formatted message text
      var message =
        "🌀 *NEW SWIRL ORDER* 🌀\n" +
        "---------------------------\n" +
        "👤 *Customer:* " + name + "\n" +
        "📞 *Contact:* " + phone + "\n" +
        "🛒 *Item:* " + product + "\n" +
        "✨ *Details:* " + details + "\n" +
        "📍 *Delivery Address:* " + address + "\n" +
        "📅 *Preferred Date:* " + date + "\n" +
        "🕒 *Preferred Time:* " + time + "\n" +
        "---------------------------\n" +
        "Sent from SWIRL Web App.";

      // Encode message for URL
      var encodedMessage = encodeURIComponent(message);

      // Create WhatsApp Link
      var waLink = "https://wa.me/" + SALESMAN_NUMBER + "?text=" + encodedMessage;

      // Open in new tab/window
      window.open(waLink, '_blank');

      // Close modal & reset form
      closeModal();
      form.reset();
    });
  }
})();
