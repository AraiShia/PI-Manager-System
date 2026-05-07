<template>
  <div class="page-container">
    <div class="page-header">
      <h2>PI管理</h2>
      <button class="add-btn" @click="$router.push('/pi/add')">+ 新建PI</button>
    </div>
    
    <div class="filter-bar">
      <select class="filter-select">
        <option value="">状态 (全部)</option>
        <option value="1">草稿</option>
        <option value="2">已确认</option>
        <option value="3">已发货</option>
        <option value="4">已完成</option>
      </select>
      <input type="text" class="search-input" placeholder="PI号/客户名称搜索" />
      <button class="search-btn">🔍</button>
    </div>
    
    <table class="data-table">
      <thead>
        <tr>
          <th><input type="checkbox" /></th>
          <th>PI号 ★</th>
          <th>客户</th>
          <th>金额(USD)</th>
          <th>收款状态</th>
          <th>出货状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pi in piList" :key="pi.id">
          <td><input type="checkbox" /></td>
          <td class="pi-no">{{ pi.pi_no }}</td>
          <td>{{ pi.customer_name }}</td>
          <td>{{ pi.total_amount }}</td>
          <td><span class="status-tag pending">{{ pi.payment_status }}</span></td>
          <td><span class="status-tag shipped">{{ pi.shipment_status }}</span></td>
          <td>{{ pi.created_at }}</td>
          <td>
            <button class="action-btn edit">编辑</button>
            <button class="action-btn view">详情</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '../utils/axios'

const piList = ref([])

onMounted(async () => {
  try {
    const response = await axios.get('/pi')
    piList.value = response.data.map(pi => ({
      ...pi,
      customer_name: 'A客户',
      payment_status: '待收款',
      shipment_status: '待出货'
    }))
  } catch (error) {
    console.error('Failed to fetch PI list:', error)
  }
})
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
  width: 250px;
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

.pi-no {
  font-weight: 600;
  color: #2563eb;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-tag.pending {
  background-color: #fef3c7;
  color: #d97706;
}

.status-tag.shipped {
  background-color: #dbeafe;
  color: #2563eb;
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

.action-btn.view {
  background-color: #d1fae5;
  color: #059669;
}
</style>
