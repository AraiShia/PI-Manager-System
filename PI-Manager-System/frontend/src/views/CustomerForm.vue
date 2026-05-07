<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑客户' : '新增客户' }}</h2>
      <button class="save-btn" @click="saveCustomer">保存</button>
    </div>
    
    <div class="form-container">
      <div class="form-section">
        <h3>基本信息</h3>
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
            <label>客户编号</label>
            <div class="auto-code-display">
              <span class="code-value">{{ isEdit ? form.customer_code : '自动生成' }}</span>
              <span class="code-hint">💡 系统自动生成3位字母/数字组合</span>
            </div>
          </div>
          <div class="form-item">
            <label>客户名称 *</label>
            <input type="text" v-model="form.customer_name" />
          </div>
          <div class="form-item">
            <label>所在国家</label>
            <input type="text" v-model="form.country" />
          </div>
          <div class="form-item">
            <label>付款条款</label>
            <input type="text" v-model="form.payment_terms" />
          </div>
        </div>
      </div>
      
      <div class="form-section">
        <h3>特殊要求 (★PI自动带出)</h3>
        <textarea v-model="form.special_require" rows="4" placeholder="输入客户的特殊要求，如包装要求、标签要求等"></textarea>
      </div>
      
      <div class="form-section">
        <h3>收货地址</h3>
        <div v-for="(addr, index) in addresses" :key="index" class="address-item">
          <div class="form-grid">
            <div class="form-item">
              <label>国家</label>
              <input type="text" v-model="addr.country" />
            </div>
            <div class="form-item">
              <label>港口</label>
              <input type="text" v-model="addr.port" />
            </div>
            <div class="form-item full">
              <label>详细地址</label>
              <input type="text" v-model="addr.address_detail" />
            </div>
          </div>
          <label class="default-checkbox">
            <input type="checkbox" v-model="addr.is_default" />
            默认地址
          </label>
          <button class="remove-btn" @click="removeAddress(index)">删除</button>
        </div>
        <button class="add-address-btn" @click="addAddress">+ 添加地址</button>
      </div>
      
      <div class="form-section">
        <h3>联系人</h3>
        <div v-for="(contact, index) in contacts" :key="index" class="contact-item">
          <div class="form-grid">
            <div class="form-item">
              <label>姓名</label>
              <input type="text" v-model="contact.name" />
            </div>
            <div class="form-item">
              <label>电话</label>
              <input type="text" v-model="contact.phone" />
            </div>
            <div class="form-item">
              <label>邮箱</label>
              <input type="text" v-model="contact.email" />
            </div>
            <div class="form-item">
              <label>职位</label>
              <input type="text" v-model="contact.position" />
            </div>
          </div>
          <label class="default-checkbox">
            <input type="checkbox" v-model="contact.is_primary" />
            主要联系人
          </label>
          <button class="remove-btn" @click="removeContact(index)">删除</button>
        </div>
        <button class="add-contact-btn" @click="addContact">+ 添加联系人</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '../utils/axios'

const isEdit = ref(false)
const customerId = ref(null)

const form = ref({
  dept_id: 'S',
  customer_code: '',
  customer_name: '',
  country: '',
  payment_terms: '',
  special_require: ''
})

const generatedCode = ref('')

const addresses = ref([
  { country: '', port: '', address_detail: '', is_default: 1 }
])

const contacts = ref([
  { name: '', phone: '', email: '', position: '', is_primary: 1 }
])

const addAddress = () => {
  addresses.value.push({ country: '', port: '', address_detail: '', is_default: 0 })
}

const removeAddress = (index) => {
  if (addresses.value.length > 1) {
    addresses.value.splice(index, 1)
  }
}

const addContact = () => {
  contacts.value.push({ name: '', phone: '', email: '', position: '', is_primary: 0 })
}

const removeContact = (index) => {
  if (contacts.value.length > 1) {
    contacts.value.splice(index, 1)
  }
}

const saveCustomer = async () => {
  try {
    const data = {
      ...form.value,
      addresses: addresses.value,
      contacts: contacts.value
    }
    if (isEdit.value) {
      await axios.put(`/customers/${customerId.value}`, data)
    } else {
      await axios.post('/customers', data)
    }
    alert('保存成功')
    window.location.href = '/customers'
  } catch (error) {
    console.error('Failed to save customer:', error)
    alert('保存失败')
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

.form-item.full {
  grid-column: span 3;
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

.auto-code-display {
  display: flex;
  flex-direction: column;
}

.code-value {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  background-color: #f8fafc;
  font-weight: 600;
  color: #3b82f6;
}

.code-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.form-section textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
}

.address-item, .contact-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  position: relative;
}

.default-checkbox {
  display: flex;
  align-items: center;
  margin: 10px 0;
  font-size: 14px;
  color: #64748b;
}

.default-checkbox input {
  margin-right: 6px;
}

.remove-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: #fee2e2;
  color: #dc2626;
  border: none;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.add-address-btn, .add-contact-btn {
  background-color: #f1f5f9;
  color: #475569;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}
</style>
