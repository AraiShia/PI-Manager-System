<template>
  <div class="page-container">
    <div class="page-header">
      <h2>供应商管理</h2>
      <button class="add-btn">+ 新增供应商</button>
    </div>
    
    <table class="data-table">
      <thead>
        <tr>
          <th><input type="checkbox" /></th>
          <th>供应商编号</th>
          <th>供应商名称</th>
          <th>地区</th>
          <th>供货周期(天)</th>
          <th>税率</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="supplier in suppliers" :key="supplier.id">
          <td><input type="checkbox" /></td>
          <td>{{ supplier.supplier_code }}</td>
          <td>{{ supplier.supplier_name }}</td>
          <td>{{ supplier.region }}</td>
          <td>{{ supplier.supply_cycle_days }}</td>
          <td>{{ supplier.tax_rate }}%</td>
          <td>
            <button class="action-btn edit">编辑</button>
            <button class="action-btn delete" @click="deleteSupplier(supplier.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '../utils/axios'

const suppliers = ref([])

onMounted(async () => {
  try {
    const response = await axios.get('/suppliers')
    suppliers.value = response.data
  } catch (error) {
    console.error('Failed to fetch suppliers:', error)
  }
})

const deleteSupplier = async (id) => {
  if (confirm('确定要删除该供应商吗？')) {
    try {
      await axios.delete(`/suppliers/${id}`)
      suppliers.value = suppliers.value.filter(s => s.id !== id)
    } catch (error) {
      console.error('Failed to delete supplier:', error)
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
</style>
