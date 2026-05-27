/* Squallcast — secondhand school clothing portal (front-end demo) */
(function () {
  "use strict";

  // ---------- Config ----------
  var BUYER_PROTECTION = 10;   // flat R10
  var COMMISSION_RATE = 0.07;  // 7%

  var CATEGORIES = [
    { id: "blazer",  label: "Blazers",     emoji: "🧥" },
    { id: "shirt",   label: "Shirts",      emoji: "👕" },
    { id: "dress",   label: "Dresses",     emoji: "👗" },
    { id: "trousers",label: "Trousers",    emoji: "👖" },
    { id: "shorts",  label: "Shorts",      emoji: "🩳" },
    { id: "skirt",   label: "Skirts",      emoji: "🩱" },
    { id: "shoes",   label: "Shoes",       emoji: "👟" },
    { id: "sport",   label: "Sports kit",  emoji: "🎽" },
    { id: "knit",    label: "Jerseys",     emoji: "🧶" },
    { id: "hat",     label: "Hats & ties", emoji: "🎓" }
  ];
  var EMOJI_OPTS = ["🧥","👕","👗","👖","🩳","🩱","👟","🎽","🧶","🎓","🧦","🎒"];

  var SEED = [
    { title: "Navy winter blazer, barely worn", category: "blazer", size: "Age 12", school: "Riverside Primary", condition: "Excellent", price: 220, emoji: "🧥", description: "Warm wool-blend blazer with school crest. Only worn one term before a growth spurt!" },
    { title: "White short-sleeve shirts (pack of 3)", category: "shirt", size: "Age 9", school: "Riverside Primary", condition: "Good", price: 90, emoji: "👕", description: "Three crisp cotton shirts, washed and ready. A couple of faint marks on collars." },
    { title: "Summer checked dress", category: "dress", size: "Age 7", school: "Sunnydale Academy", condition: "Excellent", price: 110, emoji: "👗", description: "Lovely blue gingham summer dress. Fresh and bright, no stains." },
    { title: "Grey school trousers", category: "trousers", size: "Age 10", school: "Greenfield High", condition: "Good", price: 75, emoji: "👖", description: "Adjustable-waist grey trousers. Hem let down once, plenty of wear left." },
    { title: "Black leather school shoes", category: "shoes", size: "UK 4", school: "", condition: "Well loved", price: 140, emoji: "👟", description: "Sturdy lace-ups, polished up nicely. Soles in great shape." },
    { title: "House sports vest — red", category: "sport", size: "Age 11", school: "Greenfield High", condition: "Excellent", price: 60, emoji: "🎽", description: "Breathable PE vest for the red house. Worn for one sports day." },
    { title: "Maroon V-neck jersey", category: "knit", size: "Age 8", school: "Sunnydale Academy", condition: "Good", price: 95, emoji: "🧶", description: "Cosy knit jersey with embroidered logo. Small repaired snag on the cuff." },
    { title: "Pleated tartan skirt", category: "skirt", size: "Age 13", school: "Greenfield High", condition: "Excellent", price: 130, emoji: "🩱", description: "Classic pleated skirt, adjustable waistband. Like new." },
    { title: "Navy school shorts", category: "shorts", size: "Age 6", school: "Riverside Primary", condition: "Brand new with tags", price: 70, emoji: "🩳", description: "Never worn, tags still on — bought the wrong size." },
    { title: "School cap & striped tie set", category: "hat", size: "One size", school: "Sunnydale Academy", condition: "Good", price: 45, emoji: "🎓", description: "Sun cap plus matching tie. Great spare set." },
    { title: "Sports tracksuit jacket", category: "sport", size: "Age 12", school: "Greenfield High", condition: "Excellent", price: 160, emoji: "🎽", description: "Zip-up team jacket, warm and roomy. Barely used." },
    { title: "Long-sleeve winter shirts (pair)", category: "shirt", size: "Age 11", school: "", condition: "Good", price: 80, emoji: "👕", description: "Two warm long-sleeve shirts for chilly mornings." }
  ];

  // ---------- State ----------
  var listings = [];
  var cart = [];
  var filters = { category: "all", school: "all", size: "all", q: "", sort: "new" };

  var LS_LISTINGS = "squallcast_listings_v1";
  var LS_CART = "squallcast_cart_v1";

  // ---------- Storage ----------
  function load() {
    try {
      var raw = localStorage.getItem(LS_LISTINGS);
      if (raw) listings = JSON.parse(raw);
    } catch (e) { listings = []; }
    if (!listings || !listings.length) {
      listings = SEED.map(function (s, i) {
        return Object.assign({ id: "seed-" + i, created: Date.now() - i * 3600000 }, s);
      });
      saveListings();
    }
    try {
      var c = localStorage.getItem(LS_CART);
      if (c) cart = JSON.parse(c);
    } catch (e) { cart = []; }
  }
  function saveListings() { localStorage.setItem(LS_LISTINGS, JSON.stringify(listings)); }
  function saveCart() { localStorage.setItem(LS_CART, JSON.stringify(cart)); }

  // ---------- Helpers ----------
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function rand(n) { return "id-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7) + n; }
  function rZA(n) {
    return "R" + Number(n).toLocaleString("en-ZA", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }
  function esc(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function catLabel(id) { var c = CATEGORIES.find(function (x) { return x.id === id; }); return c ? c.label : id; }
  function commission(price) { return Math.round(price * COMMISSION_RATE * 100) / 100; }
  function buyerTotal(price) { return price + BUYER_PROTECTION + commission(price); }

  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.hidden = true; }, 2200);
  }

  // ---------- Routing ----------
  var VIEWS = ["browse", "sell", "how"];
  function route() {
    var hash = location.hash.replace("#/", "") || "browse";
    if (VIEWS.indexOf(hash) === -1) hash = "browse";
    VIEWS.forEach(function (v) {
      var el = $("#view-" + v);
      if (el) el.hidden = (v !== hash);
    });
    $all(".main-nav a[data-nav]").forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-nav") === hash);
    });
    $("#main-nav, .main-nav") && $(".main-nav").classList.remove("open");
    window.scrollTo({ top: 0 });
    if (hash === "how") renderFeeExample();
  }

  // ---------- Filters UI ----------
  function uniqueValues(key) {
    var set = {};
    listings.forEach(function (l) { if (l[key]) set[l[key]] = true; });
    return Object.keys(set);
  }

  function renderFilters() {
    // category
    var catEl = $("#filter-category");
    catEl.innerHTML = chip("category", "all", "All items") +
      CATEGORIES.map(function (c) { return chip("category", c.id, c.emoji + " " + c.label); }).join("");
    // school
    var schools = uniqueValues("school");
    var schEl = $("#filter-school");
    schEl.innerHTML = chip("school", "all", "🏫 All schools") +
      schools.map(function (s) { return chip("school", s, esc(s)); }).join("");
    // size
    var sizes = uniqueValues("size");
    var szEl = $("#filter-size");
    szEl.innerHTML = chip("size", "all", "📏 All sizes") +
      sizes.map(function (s) { return chip("size", s, esc(s)); }).join("");

    $all(".chip").forEach(function (ch) {
      ch.addEventListener("click", function () {
        var f = ch.getAttribute("data-f");
        filters[f] = ch.getAttribute("data-v");
        renderGrid();
        syncChips();
      });
    });
    syncChips();
  }
  function chip(f, v, label) {
    return '<button class="chip" data-f="' + f + '" data-v="' + esc(v) + '">' + label + "</button>";
  }
  function syncChips() {
    $all(".chip").forEach(function (ch) {
      ch.classList.toggle("active", filters[ch.getAttribute("data-f")] === ch.getAttribute("data-v"));
    });
  }

  // ---------- Grid ----------
  function visibleListings() {
    var q = filters.q.trim().toLowerCase();
    var out = listings.filter(function (l) {
      if (filters.category !== "all" && l.category !== filters.category) return false;
      if (filters.school !== "all" && l.school !== filters.school) return false;
      if (filters.size !== "all" && l.size !== filters.size) return false;
      if (q) {
        var hay = (l.title + " " + l.school + " " + catLabel(l.category) + " " + l.size + " " + (l.description || "")).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
    if (filters.sort === "low") out.sort(function (a, b) { return a.price - b.price; });
    else if (filters.sort === "high") out.sort(function (a, b) { return b.price - a.price; });
    else out.sort(function (a, b) { return (b.created || 0) - (a.created || 0); });
    return out;
  }

  function renderGrid() {
    var grid = $("#browse-grid");
    var items = visibleListings();
    $("#empty-state").hidden = items.length > 0;
    $("#grid-title").textContent = filters.category === "all" ? "All listings" : catLabel(filters.category);
    grid.innerHTML = items.map(function (l) {
      return '' +
        '<article class="card product" data-id="' + l.id + '">' +
          '<div class="product-img" style="background:' + bgFor(l.category) + '">' +
            '<span class="product-cond">' + esc(l.condition) + '</span>' +
            esc(l.emoji || "👕") +
          "</div>" +
          '<div class="product-body">' +
            (l.school ? '<span class="product-school">' + esc(l.school) + "</span>" : '<span class="product-school">Squallcast</span>') +
            '<h3 class="product-title">' + esc(l.title) + "</h3>" +
            '<span class="product-meta">' + esc(catLabel(l.category)) + " · Size " + esc(l.size) + "</span>" +
            '<span class="product-price">' + rZA(l.price) + "</span>" +
          "</div>" +
        "</article>";
    }).join("");
    $all(".product", grid).forEach(function (card) {
      card.addEventListener("click", function () { openModal(card.getAttribute("data-id")); });
    });
  }

  var BGS = {
    blazer: "linear-gradient(135deg,#dbeafe,#bfdbfe)",
    shirt: "linear-gradient(135deg,#f0f9ff,#e0f2fe)",
    dress: "linear-gradient(135deg,#fce7f3,#fbcfe8)",
    trousers: "linear-gradient(135deg,#ede9fe,#ddd6fe)",
    shorts: "linear-gradient(135deg,#dcfce7,#bbf7d0)",
    skirt: "linear-gradient(135deg,#ffe4e6,#fecdd3)",
    shoes: "linear-gradient(135deg,#fef3c7,#fde68a)",
    sport: "linear-gradient(135deg,#cffafe,#a5f3fc)",
    knit: "linear-gradient(135deg,#fae8ff,#f5d0fe)",
    hat: "linear-gradient(135deg,#fef9c3,#fef08a)"
  };
  function bgFor(cat) { return BGS[cat] || "linear-gradient(135deg,#e0f2fe,#dbeafe)"; }

  // ---------- Product modal ----------
  function openModal(id) {
    var l = listings.find(function (x) { return x.id === id; });
    if (!l) return;
    var comm = commission(l.price);
    $("#modal-body").innerHTML = '' +
      '<div class="m-img" style="background:' + bgFor(l.category) + '">' + esc(l.emoji || "👕") + "</div>" +
      '<div class="m-info">' +
        (l.school ? '<span class="m-school">' + esc(l.school) + "</span>" : '<span class="m-school">Squallcast seller</span>') +
        "<h2 id=\"m-title\">" + esc(l.title) + "</h2>" +
        '<div class="m-tags">' +
          '<span class="m-tag">' + esc(catLabel(l.category)) + "</span>" +
          '<span class="m-tag">Size ' + esc(l.size) + "</span>" +
          '<span class="m-tag">' + esc(l.condition) + "</span>" +
        "</div>" +
        '<p class="m-desc">' + esc(l.description || "No description provided.") + "</p>" +
        '<div class="m-price">' + rZA(l.price) + "</div>" +
        '<div class="m-breakdown">' + breakdownHTML(l.price) + "</div>" +
        '<button class="btn btn-sun btn-lg btn-block" id="add-cart">🛒 Add to cart · ' + rZA(buyerTotal(l.price)) + "</button>" +
      "</div>";
    $("#add-cart").addEventListener("click", function () { addToCart(l.id); closeModal(); });
    $("#modal").hidden = false;
  }
  function breakdownHTML(price) {
    return '' +
      '<div class="fee-line"><span>Item price</span><span>' + rZA(price) + "</span></div>" +
      '<div class="fee-line"><span>🛡️ Buyer Protection</span><span>' + rZA(BUYER_PROTECTION) + "</span></div>" +
      '<div class="fee-line"><span>💸 Commission (7%)</span><span>' + rZA(commission(price)) + "</span></div>" +
      '<div class="fee-line total"><span>You pay</span><span>' + rZA(buyerTotal(price)) + "</span></div>";
  }
  function closeModal() { $("#modal").hidden = true; }

  // ---------- Cart ----------
  function addToCart(id) {
    cart.push(id);
    saveCart();
    updateCartCount();
    toast("Added to cart ⛅");
  }
  function removeFromCart(index) {
    cart.splice(index, 1);
    saveCart();
    updateCartCount();
    renderCart();
  }
  function updateCartCount() { $("#cart-count").textContent = cart.length; }

  function cartListings() {
    return cart.map(function (id) { return listings.find(function (l) { return l.id === id; }); })
               .filter(Boolean);
  }

  function renderCart() {
    var body = $("#cart-body");
    var items = cartListings();
    if (!items.length) {
      body.innerHTML = '<div class="cart-empty"><span class="big">🛒</span>Your cart is empty.<br>Find a uniform to fill it with sunshine!</div>';
      return;
    }
    var subtotal = 0, comm = 0, protect = 0;
    var rows = items.map(function (l, i) {
      subtotal += l.price;
      comm += commission(l.price);
      protect += BUYER_PROTECTION;
      return '' +
        '<div class="cart-item">' +
          '<div class="ci-img" style="background:' + bgFor(l.category) + '">' + esc(l.emoji || "👕") + "</div>" +
          '<div class="ci-body">' +
            '<div class="ci-title">' + esc(l.title) + "</div>" +
            '<div class="ci-meta">Size ' + esc(l.size) + " · " + esc(l.condition) + "</div>" +
            '<div class="ci-price">' + rZA(l.price) + "</div>" +
          "</div>" +
          '<button class="ci-remove" data-i="' + i + '" aria-label="Remove">🗑️</button>' +
        "</div>";
    }).join("");
    var total = subtotal + comm + protect;

    body.innerHTML = rows +
      '<div class="cart-summary">' +
        '<div class="fee-line"><span>Items (' + items.length + ")</span><span>" + rZA(subtotal) + "</span></div>" +
        '<div class="fee-line"><span>🛡️ Buyer Protection</span><span>' + rZA(protect) + "</span></div>" +
        '<div class="fee-line"><span>💸 Commission (7%)</span><span>' + rZA(comm) + "</span></div>" +
        '<div class="fee-line total"><span>Total</span><span>' + rZA(total) + "</span></div>" +
        '<button class="btn btn-primary btn-lg btn-block" id="checkout-btn" style="margin-top:.8rem">Checkout · ' + rZA(total) + "</button>" +
        '<p class="hint" style="text-align:center;color:var(--muted);font-weight:600;font-size:.8rem;margin:.6rem 0 0">Every order is covered by R10 Buyer Protection 🛡️</p>' +
      "</div>";

    $all(".ci-remove", body).forEach(function (b) {
      b.addEventListener("click", function () { removeFromCart(Number(b.getAttribute("data-i"))); });
    });
    $("#checkout-btn").addEventListener("click", checkout);
  }

  function checkout() {
    var items = cartListings();
    if (!items.length) return;
    var total = items.reduce(function (s, l) { return s + buyerTotal(l.price); }, 0);
    toast("🎉 Order placed! Total " + rZA(total));
    cart = [];
    saveCart();
    updateCartCount();
    renderCart();
    setTimeout(closeCart, 600);
  }

  function openCart() { renderCart(); $("#cart-drawer").hidden = false; }
  function closeCart() { $("#cart-drawer").hidden = true; }

  // ---------- Sell form ----------
  function initSellForm() {
    var sel = $("#f-category");
    sel.innerHTML = '<option value="">Choose…</option>' +
      CATEGORIES.map(function (c) { return '<option value="' + c.id + '">' + c.emoji + " " + c.label + "</option>"; }).join("");

    var dl = $("#school-list");
    dl.innerHTML = uniqueValues("school").map(function (s) { return '<option value="' + esc(s) + '">'; }).join("");

    var picker = $("#emoji-picker");
    picker.innerHTML = EMOJI_OPTS.map(function (e) { return '<button type="button" class="emoji-opt" data-e="' + e + '">' + e + "</button>"; }).join("");
    var chosen = { emoji: "" };
    $all(".emoji-opt", picker).forEach(function (b) {
      b.addEventListener("click", function () {
        $all(".emoji-opt", picker).forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        chosen.emoji = b.getAttribute("data-e");
      });
    });

    // live payout hint
    $("#f-price").addEventListener("input", function () {
      var p = parseFloat(this.value);
      var hint = $("#payout-hint");
      if (p > 0) {
        hint.innerHTML = "You receive <strong>" + rZA(p) + "</strong>. Buyer pays <strong>" +
          rZA(buyerTotal(p)) + "</strong> (incl. R10 protection + " + rZA(commission(p)) + " commission).";
      } else {
        hint.textContent = "You'll receive your full asking price. Buyers pay a R10 buyer protection fee and 7% commission on top.";
      }
    });

    $("#sell-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var form = e.target;
      var ok = true;
      $all(".field", form).forEach(function (f) { f.classList.remove("invalid"); });
      ["title", "category", "size", "condition", "price"].forEach(function (name) {
        var input = form.elements[name];
        if (!input.value.trim()) { input.closest(".field").classList.add("invalid"); ok = false; }
      });
      if (!chosen.emoji) { $("#emoji-picker").closest(".field").classList.add("invalid"); ok = false; }
      if (!ok) { toast("Please fill the highlighted fields ⛅"); return; }

      var listing = {
        id: rand(listings.length),
        title: form.elements.title.value.trim(),
        category: form.elements.category.value,
        size: form.elements.size.value.trim(),
        school: form.elements.school.value.trim(),
        condition: form.elements.condition.value,
        price: Math.max(1, Math.round(parseFloat(form.elements.price.value))),
        emoji: chosen.emoji,
        description: form.elements.description.value.trim(),
        created: Date.now()
      };
      listings.unshift(listing);
      saveListings();
      renderFilters();
      renderGrid();

      form.reset();
      $all(".emoji-opt").forEach(function (x) { x.classList.remove("active"); });
      chosen.emoji = "";
      $("#payout-hint").textContent = "You'll receive your full asking price. Buyers pay a R10 buyer protection fee and 7% commission on top.";
      $("#sell-msg").textContent = "Published! 🎉";
      toast("Listing published ⛅");
      setTimeout(function () { $("#sell-msg").textContent = ""; location.hash = "#/browse"; }, 900);
    });
  }

  // ---------- Fee example (How it works) ----------
  function renderFeeExample() {
    var price = 120;
    $("#fee-example").innerHTML =
      "<h3>Worked example: a R" + price + " jersey</h3>" + breakdownHTML(price) +
      '<div class="fee-line payout"><span>✅ Seller receives</span><span>' + rZA(price) + "</span></div>";
  }

  // ---------- Wire up ----------
  function init() {
    load();
    renderFilters();
    renderGrid();
    initSellForm();
    updateCartCount();

    $("#search-form").addEventListener("submit", function (e) { e.preventDefault(); });
    $("#search-input").addEventListener("input", function () {
      filters.q = this.value;
      if (location.hash.replace("#/", "") !== "browse" && location.hash !== "") location.hash = "#/browse";
      renderGrid();
    });
    $("#sort").addEventListener("change", function () { filters.sort = this.value; renderGrid(); });

    $("#cart-btn").addEventListener("click", openCart);
    $("#cart-close").addEventListener("click", closeCart);
    $("#cart-drawer").addEventListener("click", function (e) { if (e.target === this) closeCart(); });

    $("#modal-close").addEventListener("click", closeModal);
    $("#modal").addEventListener("click", function (e) { if (e.target === this) closeModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeModal(); closeCart(); }
    });

    $("#menu-toggle").addEventListener("click", function () { $(".main-nav").classList.toggle("open"); });
    $all(".main-nav a").forEach(function (a) {
      a.addEventListener("click", function () { $(".main-nav").classList.remove("open"); });
    });

    window.addEventListener("hashchange", route);
    route();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
