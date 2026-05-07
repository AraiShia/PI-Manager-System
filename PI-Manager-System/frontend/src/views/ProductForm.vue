<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑产品' : '新增产品' }}</h2>
      <button class="save-btn" @click="saveProduct">保存</button>
    </div>
    
    <div class="form-container">
      <div class="form-section">
        <h3>基础信息</h3>
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
            <label>系统编号</label>
            <input type="text" v-model="form.product_code" readonly />
          </div>
          <div class="form-item">
            <label>OE号 *</label>
            <input type="text" v-model="form.oe_number" />
          </div>
          <div class="form-item">
            <label>工厂编号</label>
            <input type="text" v-model="form.factory_code" />
          </div>
          <div class="form-item">
            <label>品牌</label>
            <input type="text" v-model="form.brand" />
          </div>
          <div class="form-item">
            <label>产品类别</label>
            <select v-model="form.category_id">
              <option value="1">发动机</option>
              <option value="2">变速箱</option>
              <option value="3">底盘</option>
            </select>
          </div>
          <div class="form-item full">
            <label>细节描述 *</label>
            <textarea v-model="form.detail_desc" rows="3"></textarea>
          </div>
        </div>
      </div>
      
      <div class="form-section">
        <h3>供应商信息</h3>
        <div class="form-grid">
          <div class="form-item">
            <label>主要供应商</label>
            <select v-model="form.supplier_id">
              <option value="">选择供应商</option>
            </select>
          </div>
          <div class="form-item">
            <label>采购渠道</label>
            <select v-model="form.purchase_channel">
              <option value="1688">1688</option>
              <option value="alibaba">阿里巴巴国际站</option>
              <option value="factory">工厂直采</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="form-section">
        <h3>价格信息</h3>
        <div class="form-grid">
          <div class="form-item">
            <label>EXW含税价</label>
            <input type="number" step="0.01" v-model="form.exw_price_incl" />
          </div>
          <div class="form-item">
            <label>EXW不含税</label>
            <input type="number" step="0.01" v-model="form.exw_price_excl" />
          </div>
          <div class="form-item">
            <label>FOB含税价</label>
            <input type="number" step="0.01" v-model="form.fob_price_incl" />
          </div>
          <div class="form-item">
            <label>FOB不含税</label>
            <input type="number" step="0.01" v-model="form.fob_price_excl" />
          </div>
          <div class="form-item">
            <label>运费</label>
            <input type="number" step="0.01" v-model="form.freight" />
          </div>
          <div class="form-item">
            <label>包装费</label>
            <input type="number" step="0.01" v-model="form.packing_fee" />
          </div>
        </div>
      </div>
      
      <div class="form-section">
        <h3>包装体积 ★</h3>
        <div class="form-grid">
          <div class="form-item">
            <label>纸箱长度(cm)</label>
            <input type="number" step="0.1" v-model="form.carton_length_cm" />
          </div>
          <div class="form-item">
            <label>纸箱宽度(cm)</label>
            <input type="number" step="0.1" v-model="form.carton_width_cm" />
          </div>
          <div class="form-item">
            <label>纸箱高度(cm)</label>
            <input type="number" step="0.1" v-model="form.carton_height_cm" />
          </div>
          <div class="form-item">
            <label>每箱数量 *</label>
            <input type="number" v-model="form.units_per_carton" />
          </div>
          <div class="form-item">
            <label>每箱体积(m³)</label>
            <input type="text" :value="cartonVolume" readonly />
          </div>
          <div class="form-item">
            <label>每箱毛重(kg)</label>
            <input type="number" step="0.1" v-model="form.gross_weight_kg" />
          </div>
        </div>
      </div>
      
      <div class="form-section">
        <h3>产品图片</h3>
        <div class="upload-area">
          <button class="upload-btn">+ 上传图片</button>
          <span class="upload-hint">拖拽或点击上传 (支持jpg/png，建议800x800)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from '../utils/axios'

const isEdit = ref(false)
const productId = ref(null)

const form = ref({
  dept_id: 'S',
  product_code: '',
  oe_number: '',
  factory_code: '',
  brand: '',
  detail_desc: '',
  supplier_id: '',
  purchase_channel: '1688',
  exw_price_incl: '',
  exw_price_excl: '',
  fob_price_incl: '',
  fob_price_excl: '',
  freight: '',
  packing_fee: '',
  carton_length_cm: '',
  carton_width_cm: '',
  carton_height_cm: '',
  units_per_carton: '',
  gross_weight_kg: '',
  category_id: 1
})

const cartonVolume = computed(() => {
  const length = parseFloat(form.value.carton_length_cm) || 0
  const width = parseFloat(form.value.carton_width_cm) || 0
  const height = parseFloat(form.value.carton_height_cm) || 0
  if (length && width && height) {
    return ((length * width * height) / 1000000).toFixed(6)
  }
  return '自动计算'
})

onMounted(async () => {
  const path = window.location.pathname
  if (path.includes('/products/') && path !== '/products/add') {
    isEdit.value = true
    productId.value = parseInt(path.split('/')[2])
    try {
      const response = await axios.get(`/products/${productId.value}`)
      form.value = { ...form.value, ...response.data }
    } catch (error) {
      console.error('Failed to fetch product:', error)
    }
  }
})

const saveProduct = async () => {
  try {
    if (isEdit.value) {
      await axios.put(`/products/${productId.value}`, form.value)
    } else {
      await axios.post('/products', form.value)
    }
    alert('保存成功')
    window.location.href = '/products'
  } catch (error) {
    console.error('Failed to save product:', error)
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
  color: #1e293b;
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

.form-item input, .form-item select, .form-item textarea {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.form-item textarea {
  resize: vertical;
}

.form-item input[readonly] {
  background-color: #f8fafc;
  color: #94a3b8;
}

.upload-area {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
}

.upload-btn {
  background-color: #2563eb;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 14px;
  color: #94a3b8;
}
</style>
