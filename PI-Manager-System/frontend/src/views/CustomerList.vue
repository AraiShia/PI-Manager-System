<template>
  <div class="page-container">
    <div class="page-header">
      <h2>客户管理</h2>
      <button class="add-btn" @click="$router.push('/customers/add')">+ 新增客户</button>
    </div>
    
    <table class="data-table">
      <thead>
        <tr>
          <th><input type="checkbox" /></th>
          <th>客户编号</th>
          <th>客户名称</th>
          <th>国家</th>
          <th>付款条款</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="customer in customers" :key="customer.id">
          <td><input type="checkbox" /></td>
          <td>{{ customer.customer_code }}</td>
          <td>{{ customer.customer_name }}</td>
          <td>{{ customer.country }}</td>
          <td>{{ customer.payment_terms }}</td>
          <td>
            <button class="action-btn edit">编辑</button>
            <button class="action-btn delete" @click="deleteCustomer(customer.id)">删除</button>
            <button class="action-btn view">详情</button>
          </td>
        </tr>
      </tbody>
    </table>
    
    <div class="pagination">
      <span>显示 1-10 共 50 条</span>
      <div class="pagination-nav">
        <button>&lt;</button>
        <button class="active">1</button>
        <button>2</button>
        <button>3</button>
        <button>...</button>
        <button>5</button>
        <button>&gt;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '../utils/axios'

const customers = ref([])

onMounted(async () => {
  try {
    const response = await axios.get('/customers')
    customers.value = response.data
  } catch (error) {
    console.error('Failed to fetch customers:', error)
  }
})

const deleteCustomer = async (id) => {
  if (confirm('确定要删除该客户吗？')) {
    try {
      await axios.delete(`/customers/${id}`)
      customers.value = customers.value.filter(c => c.id !== id)
    } catch (error) {
      console.error('Failed to delete customer:', error)
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

.action-btn.view {
  background-color: #d1fae5;
  color: #059669;
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
