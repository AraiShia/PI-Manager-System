<template>
  <div class="dashboard">
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon pending">📋</div>
        <div class="stat-info">
          <div class="stat-value">12</div>
          <div class="stat-label">待处理PI</div>
          <div class="stat-change">↑ 20%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon shipment">🚚</div>
        <div class="stat-info">
          <div class="stat-value">8</div>
          <div class="stat-label">本月出货</div>
          <div class="stat-change">↑ 15%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon payment">💰</div>
        <div class="stat-info">
          <div class="stat-value">$45,230</div>
          <div class="stat-label">待收款</div>
          <div class="stat-change">↓ 5%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon warning">⚠️</div>
        <div class="stat-info">
          <div class="stat-value">3</div>
          <div class="stat-label">库存预警</div>
        </div>
      </div>
    </div>
    
    <div class="dashboard-grid">
      <div class="recent-pi">
        <h3>最近PI单</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>PI号</th>
              <th>客户</th>
              <th>金额</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pi in recentPI" :key="pi.pi_no">
              <td>{{ pi.pi_no }}</td>
              <td>{{ pi.customer_name }}</td>
              <td>${{ pi.total_amount }}</td>
            </tr>
          </tbody>
        </table>
        <a href="/pi" class="view-all">查看全部 →</a>
      </div>
      
      <div class="pending-tasks">
        <h3>待处理事项</h3>
        <ul class="task-list">
          <li v-for="task in pendingTasks" :key="task.id">
            <input type="checkbox" :id="'task-' + task.id" />
            <label :for="'task-' + task.id">{{ task.text }}</label>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const recentPI = ref([
  { pi_no: 'SA012612011', customer_name: 'A客户', total_amount: 5230 },
  { pi_no: 'SA012612010', customer_name: 'B客户', total_amount: 3120 },
  { pi_no: 'SA012612009', customer_name: 'C客户', total_amount: 8450 }
])

const pendingTasks = ref([
  { id: 1, text: 'PI #SA012612011 待确认' },
  { id: 2, text: '采购单#VSA01 待入库' },
  { id: 3, text: '收款 $2,000 待确认' },
  { id: 4, text: '库存产品X超期30天' }
])
</script>

<style scoped>
.dashboard {
  padding: 24px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  background-color: #fff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-right: 16px;
}

.stat-icon.pending {
  background-color: #feebc8;
}

.stat-icon.shipment {
  background-color: #d1fae5;
}

.stat-icon.payment {
  background-color: #dbeafe;
}

.stat-icon.warning {
  background-color: #fef3c7;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
}

.stat-change {
  font-size: 12px;
  color: #10b981;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.recent-pi, .pending-tasks {
  background-color: #fff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

h3 {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.data-table th {
  font-weight: 600;
  color: #64748b;
  font-size: 14px;
}

.data-table td {
  font-size: 14px;
}

.view-all {
  display: inline-block;
  margin-top: 12px;
  color: #2563eb;
  text-decoration: none;
  font-size: 14px;
}

.task-list {
  list-style: none;
}

.task-list li {
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
}

.task-list li:last-child {
  border-bottom: none;
}

.task-list input[type="checkbox"] {
  margin-right: 10px;
}

.task-list label {
  font-size: 14px;
  color: #334155;
}
</style>
