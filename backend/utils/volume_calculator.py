class VolumeCalculator:
    @staticmethod
    def calculate_carton_volume(length_cm: float, width_cm: float, height_cm: float) -> float:
        """计算每箱体积（立方米）"""
        return (length_cm * width_cm * height_cm) / 1000000
    
    @staticmethod
    def calculate_shipping_volume(quantity: float, units_per_carton: int, carton_volume_m3: float) -> tuple:
        """计算出货体积"""
        cartons = (quantity + units_per_carton - 1) // units_per_carton  # 向上取整
        total_volume = cartons * carton_volume_m3
        return cartons, total_volume
    
    @staticmethod
    def calculate_gross_weight(cartons: float, weight_per_carton: float) -> float:
        """计算总毛重"""
        return cartons * weight_per_carton
