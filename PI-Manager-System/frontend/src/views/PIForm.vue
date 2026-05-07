<template>
  <div class="page-container">
    <div class="page-header">
      <h2>新建PI单</h2>
      <button class="save-btn" @click="savePI">保存</button>
    </div>
    
    <div class="form-container">
      <div class="form-section">
        <h3>基本信息 ★</h3>
        <div class="form-grid">
          <div class="form-item">
            <label>部门 *</label>
            <select v-model="form.dept_id">
              <option value="S">索英普(S)</option>
              <option value="W">维那(W)</option>
              <option value="M">马迪那(M)</option>
              <option value="D">银达(D)</option>
            </select>
          </div>
          <div class="form-item">
            <label>PI号</label>
            <input type="text" :value="piNumber" readonly />
          </div>
          <div class="form-item">
            <label>客户 *</label>
            <select v-model="form.customer_id" @change="onCustomerChange">
              <option value="">选择客户</option>
              <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.customer_name }}</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="form-section">
        <h3>客户特殊要求</h3>
        <textarea :value="customerSpecialRequire" readonly rows="2" class="readonly-textarea"></textarea>
      </div>
      
      <div class="form-section">
        <h3>产品明细 ★</h3>
        <div class="product-table-container">
          <table class="product-table">
            <thead>
              <tr>
                <th>选择产品</th>
                <th>OE号</th>
                <th>产品描述</th>
                <th>单价(USD)</th>
                <th>数量</th>
                <th>金额(USD)</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in items" :key="index">
                <td>
                  <select v-model="item.product_id" @change="onProductChange(index)">
                    <option value="">选择产品</option>
                    <option v-for="p in products" :key="p.id" :value="p.id">{{ p.oe_number }}</option>
                  </select>
                </td>
                <td>{{ item.oe_number }}</td>
                <td>{{ item.detail_desc }}</td>
                <td><input type="number" step="0.01" v-model="item.unit_price" @input="updateTotal(index)" /></td>
                <td><input type="number" v-model="item.quantity" @input="updateTotal(index)" /></td>
                <td>{{ item.total_price }}</td>
                <td><button class="remove-item-btn" @click="removeItem(index)">×</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <button class="add-item-btn" @click="addItem">+ 添加产品</button>
      </div>
      
      <div class="form-section">
        <h3>金额总计</h3>
        <div class="total-row">
          <span>合计金额:</span>
          <span class="total-amount">${{ totalAmount }}</span>
        </div>
      </div>
      
      <div class="form-section">
        <h3>付款条款 ★</h3>
        <div v-for="(stage, index) in paymentStages" :key="index" class="stage-item">
          <div class="form-grid">
            <div class="form-item">
              <label>阶段{{ index + 1 }}类型</label>
              <select v-model="stage.stage_type">
                <option value="DEPOSIT">定金</option>
                <option value="BALANCE">尾款</option>
                <option value="T/T">电汇</option>
              </select>
            </div>
            <div class="form-item">
              <label>金额(USD)</label>
              <input type="number" step="0.01" v-model="stage.amount" />
            </div>
            <div class="form-item">
              <label>到期日期</label>
              <input type="date" v-model="stage.due_date" />
            </div>
          </div>
        </div>
        <button class="add-stage-btn" @click="addPaymentStage">+ 添加付款阶段</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from '../utils/axios'

const form = ref({
  dept_id: 'S',
  customer_id: ''
})

const piNumber = ref('自动生成')
const customerSpecialRequire = ref('')

const customers = ref([])
const products = ref([])

const items = ref([
  { product_id: '', oe_number: '', detail_desc: '', unit_price: '', quantity: '', total_price: '' }
])

const paymentStages = ref([
  { stage_type: 'DEPOSIT', stage_no: 1, amount: '', due_date: '' },
  { stage_type: 'BALANCE', stage_no: 2, amount: '', due_date: '' }
])

const totalAmount = computed(() => {
  return items.value.reduce((sum, item) => {
    const price = parseFloat(item.unit_price) || 0
    const qty = parseFloat(item.quantity) || 0
    return sum + price * qty
  }, 0).toFixed(2)
})

onMounted(async () => {
  try {
    const [customerRes, productRes] = await Promise.all([
      axios.get('/customers'),
      axios.get('/products')
    ])
    customers.value = customerRes.data
    products.value = productRes.data
  } catch (error) {
    console.error('Failed to fetch data:', error)
  }
})

const onCustomerChange = async () => {
  if (!form.value.customer_id) return
  const customer = customers.value.find(c => c.id === parseInt(form.value.customer_id))
  if (customer) {
    customerSpecialRequire.value = customer.special_require || '无特殊要求'
  }
}

const onProductChange = (index) => {
  const productId = parseInt(items.value[index].product_id)
  const product = products.value.find(p => p.id === productId)
  if (product) {
    items.value[index].oe_number = product.oe_number
    items.value[index].detail_desc = product.detail_desc
  }
}

const updateTotal = (index) => {
  const price = parseFloat(items.value[index].unit_price) || 0
  const qty = parseFloat(items.value[index].quantity) || 0
  items.value[index].total_price = (price * qty).toFixed(2)
}

const addItem = () => {
  items.value.push({ product_id: '', oe_number: '', detail_desc: '', unit_price: '', quantity: '', total_price: '' })
}

const removeItem = (index) => {
  if (items.value.length > 1) {
    items.value.splice(index, 1)
  }
}

const addPaymentStage = () => {
  paymentStages.value.push({
    stage_type: 'T/T',
    stage_no: paymentStages.value.length + 1,
    amount: '',
    due_date: ''
  })
}

const savePI = async () => {
  try {
    const data = {
      dept_id: form.value.dept_id,
      customer_id: parseInt(form.value.customer_id),
      items: items.value.map(item => ({
        product_id: parseInt(item.product_id),
        unit_price: parseFloat(item.unit_price),
        quantity: parseFloat(item.quantity),
        customer_code: '',
        detail_desc: item.detail_desc,
        remark: ''
      })),
      payment_stages: paymentStages.value.map(stage => ({
        stage_type: stage.stage_type,
        stage_no: stage.stage_no,
        amount: parseFloat(stage.amount),
        due_date: stage.due_date
      })),
      currency: 'USD'
    }
    await axios.post('/pi', data)
    alert('PI创建成功')
    window.location.href = '/pi'
  } catch (error) {
    console.error('Failed to create PI:', error)
    alert('创建失败')
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

.save-btn {
  background-color: #2563eb;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}

.form-container {
  background-color: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.form-section {
  margin-bottom: 24px;
}

.form-section h3 {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
}

.form-item label {
  margin-bottom: 6px;
  font-size: 14px;
  color: #475569;
}

.form-item input, .form-item select {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.readonly-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  background-color: #f8fafc;
  color: #64748b;
}

.product-table-container {
  overflow-x: auto;
}

.product-table {
  width: 100%;
  border-collapse: collapse;
}

.product-table th, .product-table td {
  padding: 10px;
  border: 1px solid #e2e8f0;
  text-align: left;
}

.product-table th {
  background-color: #f8fafc;
  font-weight: 600;
}

.product-table select, .product-table input {
  width: 100%;
  padding: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.remove-item-btn {
  background-color: #fee2e2;
  color: #dc2626;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
}

.add-item-btn {
  margin-top: 12px;
  background-color: #f1f5f9;
  color: #475569;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}

.total-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  font-size: 18px;
}

.total-row span:first-child {
  margin-right: 12px;
  color: #64748b;
}

.total-amount {
  font-weight: 700;
  color: #2563eb;
}

.stage-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.add-stage-btn {
  background-color: #f1f5f9;
  color: #475569;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}
</style>
