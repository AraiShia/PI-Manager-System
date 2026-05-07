<template>
  <div class="page-container">
    <div class="page-header">
      <h2>产品管理</h2>
      <button class="add-btn" @click="$router.push('/products/add')">+ 新增产品</button>
    </div>
    
    <div class="filter-bar">
      <select class="filter-select">
        <option value="">部门 (全部)</option>
        <option value="S">索英普(S)</option>
        <option value="W">维那(W)</option>
        <option value="M">马迪那(M)</option>
        <option value="D">银达(D)</option>
      </select>
      <select class="filter-select">
        <option value="">类别 (全部)</option>
        <option value="1">发动机</option>
        <option value="2">变速箱</option>
      </select>
      <input type="text" class="search-input" placeholder="OE号搜索" v-model="searchQuery" />
      <button class="search-btn">🔍</button>
    </div>
    
    <table class="data-table">
      <thead>
        <tr>
          <th><input type="checkbox" /></th>
          <th>系统编号</th>
          <th>OE号</th>
          <th>品牌</th>
          <th>每箱数量</th>
          <th>库存(待出)</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="product in products" :key="product.id">
          <td><input type="checkbox" /></td>
          <td>{{ product.product_code }}</td>
          <td>{{ product.oe_number }}</td>
          <td>{{ product.brand }}</td>
          <td>{{ product.units_per_carton }} pcs</td>
          <td>--</td>
          <td>
            <button class="action-btn edit" @click="$router.push(`/products/${product.id}`)">编辑</button>
            <button class="action-btn delete" @click="deleteProduct(product.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    
    <div class="pagination">
      <span>显示 1-10 共 128 条</span>
      <div class="pagination-nav">
        <button>&lt;</button>
        <button class="active">1</button>
        <button>2</button>
        <button>3</button>
        <button>...</button>
        <button>32</button>
        <button>&gt;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '../utils/axios'

const products = ref([])
const searchQuery = ref('')

onMounted(async () => {
  try {
    const response = await axios.get('/products')
    products.value = response.data
  } catch (error) {
    console.error('Failed to fetch products:', error)
  }
})

const deleteProduct = async (id) => {
  if (confirm('确定要删除该产品吗？')) {
    try {
      await axios.delete(`/products/${id}`)
      products.value = products.value.filter(p => p.id !== id)
    } catch (error) {
      console.error('Failed to delete product:', error)
    }
  }
}
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
}

.add-btn {
  background-color: #2563eb;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}

.add-btn:hover {
  background-color: #1d4ed8;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  width: 200px;
}

.search-btn {
  background-color: #2563eb;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}

.data-table {
  width: 100%;
  background-color: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.data-table th {
  background-color: #f8fafc;
  font-weight: 600;
  color: #64748b;
}

.data-table tr:hover {
  background-color: #f8fafc;
}

.action-btn {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  margin-right: 4px;
}

.action-btn.edit {
  background-color: #dbeafe;
  color: #2563eb;
}

.action-btn.delete {
  background-color: #fee2e2;
  color: #dc2626;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}

.pagination span {
  color: #64748b;
  font-size: 14px;
}

.pagination-nav button {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  margin: 0 2px;
}

.pagination-nav button.active {
  background-color: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
</style>
