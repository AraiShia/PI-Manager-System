<template>
  <aside class="sidebar">
    <div class="logo-section">
      <h2>PI订单系统</h2>
    </div>
    <nav class="nav-menu">
      <router-link to="/" class="nav-item" :class="{ active: $route.name === 'Dashboard' }">
        <span class="icon">📊</span>
        <span>看板</span>
      </router-link>
      <router-link to="/products" class="nav-item" :class="{ active: $route.name.includes('Product') }">
        <span class="icon">📦</span>
        <span>产品管理</span>
      </router-link>
      <router-link to="/customers" class="nav-item" :class="{ active: $route.name.includes('Customer') }">
        <span class="icon">👥</span>
        <span>客户管理</span>
      </router-link>
      <router-link to="/suppliers" class="nav-item" :class="{ active: $route.name.includes('Supplier') }">
        <span class="icon">🏭</span>
        <span>供应商管理</span>
      </router-link>
      <router-link to="/pi" class="nav-item pi-active" :class="{ active: $route.name.includes('PI') }">
        <span class="icon">📄</span>
        <span>PI管理</span>
        <span class="badge">★</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup>
</script>

<style scoped>
.sidebar {
  width: 240px;
  background-color: #1e293b;
  color: #fff;
  padding: 20px 0;
  flex-shrink: 0;
}

.logo-section {
  padding: 0 20px 20px;
  border-bottom: 1px solid #334155;
}

.logo-section h2 {
  font-size: 18px;
  font-weight: 600;
  color: #2563eb;
}

.nav-menu {
  margin-top: 20px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: #cbd5e1;
  text-decoration: none;
  transition: background-color 0.2s;
}

.nav-item:hover {
  background-color: #334155;
}

.nav-item.active {
  background-color: #2563eb;
  color: #fff;
}

.icon {
  margin-right: 10px;
  font-size: 18px;
}

.badge {
  margin-left: auto;
  background-color: #f59e0b;
  color: #1e293b;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
}
</style>
