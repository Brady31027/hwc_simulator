from enum import Enum

class ColorFormat(Enum):
	HAL_PIXEL_FORMAT_RGBA_8888    = "rgba8888"
	HAL_PIXEL_FORMAT_BGRA_8888    = "bgra8888"
	HAL_PIXEL_FORMAT_RGB_565      = "rgb565"
	HAL_PIXEL_FORMAT_RGBA_1010102 = "rgba1010102"

class HDR(Enum):
	SDR   = "sdr"
	HDR10 = "hdr10"
	HLG   = "hlg"

class Label(Enum):
	DEVICE_SDR = "device_sdr"
	DEVICE_HDR10 = "device_hdr10"
	DEVICE_HLG = "device_hlg"
	CLIENT_SDR = "client_sdr"
	CLIENT_HDR10 = "client_hdr10"
	CLIENT_HLG = "client_hlg"

class RefreshRate(Enum):
	FPS_60  = "60fps"
	FPS_120 = "120fps"

class GOP(Enum):
	GOP0 = 0
	GOP1 = 1
	GOP2 = 2
	GOP3 = 3

class Layer:
	def __init__(self, hdr=HDR.SDR, format=ColorFormat.HAL_PIXEL_FORMAT_RGBA_8888, is_scale_down=False, is_rotate=False):
		self.hdr = hdr
		self.format = format
		self.is_scale_down = is_scale_down
		self.is_rotate = is_rotate

class Result:
	def __init__(self, layer, label=Label.DEVICE_SDR, gop=GOP.GOP0):
		self.layer = layer
		self.label = label
		self.gop = gop

class Verifier:
	def __init__(self, layer):
		self.layer = layer

	def get_fmt(self, composer=True):
		if composer == False:
			if self.layer.hdr == HDR.SDR:
				return Label.CLIENT_SDR
			elif self.layer.hdr == HDR.HDR10:
				return Label.CLIENT_HDR10
			elif self.layer.hdr == HDR.HLG:
				return Label.CLIENT_HLG
		else:
			if self.layer.hdr == HDR.SDR:
				return Label.DEVICE_SDR
			elif self.layer.hdr == HDR.HDR10:
				return Label.DEVICE_HDR10
			elif self.layer.hdr == HDR.HLG:
				return Label.DEVICE_HLG

	def verify(self):
		if self.layer.is_scale_down:
			#print("reject because of scale down")
			return self.get_fmt(False)
		if self.layer.is_rotate:
			#print("reject because of rotate")
			return self.get_fmt(False)
		if self.layer.format not in ColorFormat._value2member_map_:
			#print("reject because of color fmt")
			return self.get_fmt(False)
		#print("accept")
		return self.get_fmt(True)

class Util:
	def __init__(self, layer):
		self.layer = layer

	def is_hdr(self):
		return True if self.layer.hdr == HDR.HDR10 or self.layer.hdr == HDR.HLG else False

class Template_Cache:
	def __init__(self, layers, metadata):
		self.layers = layers
		self.metadata = metadata

	def is_cache_hit(self):
		# early determination if layer count <= 4
		if len(self.layers) < 5:
			for i in range(len(self.layers)):
				hwc_verification_result.append(Result(self.layers[i], self.metadata[i], GOP._value2member_map_[i]))
			return True
		# TODO: add more cache entries based on real scenarios
		return False


class Dispatcher:
	def __init__(self, layers, metadata):
		self.layers = layers
		self.metadata = metadata

	def get_penalty(self, layer, metadata):
		is_composed_by_client = 1 if "CLIENT" in str(metadata) else 0
		is_sdr_content = 1 if Util(layer).is_hdr == False else 0
		return (is_composed_by_client << 1) | is_sdr_content

	def is_neighbor_layer(self, candidates, layer):
		layer_index = layer[0]
		for candidate in candidates:
			if abs(layer_index - candidate[0]) == 1:
				return True
		return False

	def dispatch(self):
		if len(self.layers) < 5:
			print("[Error] Should have hit if layer count less than 5")
			return False
		if len(self.layers) == 5:
			max_penalty_score = -1
			layer_index_of_gpu_composition = -1
			
			for i in range(len(self.layers) - 1):
				current_penalty = self.get_penalty(self.layers[i], self.metadata[i])
				next_penalty = self.get_penalty(self.layers[i+1], self.metadata[i+1])
				total_penalty_score = current_penalty + next_penalty
				if total_penalty_score > max_penalty_score:
					max_penalty_score = total_penalty_score
					layer_index_of_gpu_composition = i

			gop_idx = 0
			for i in range(len(self.layers) - 1):
				if i == layer_index_of_gpu_composition:
					hwc_verification_result.append(Result(self.layers[i], self.metadata[i], GOP._value2member_map_[gop_idx]))
					hwc_verification_result.append(Result(self.layers[i+1], self.metadata[i+1], GOP._value2member_map_[gop_idx]))
				else:
					hwc_verification_result.append(Result(self.layers[i], self.metadata[i], GOP._value2member_map_[gop_idx]))
				gop_idx += 1
			return True

		elif len(self.layers) == 6:
			penalty_table = []
			for i in range(len(self.layers) - 1):
				current_penalty = self.get_penalty(self.layers[i], self.metadata[i])
				next_penalty = self.get_penalty(self.layers[i+1], self.metadata[i+1])
				total_penalty_score = current_penalty + next_penalty
				penalty_table.append([i, total_penalty_score])
			sorted_penalty_table = sorted(penalty_table, key=lambda k: k[1], reverse=True)
			num_of_gpu_composition = len(self.layers) - 4 #TODO: Need to consider 120Hz panel
			gpu_composed_layers = []
			for ele in sorted_penalty_table:
				if self.is_neighbor_layer(gpu_composed_layers, ele) == False:
					gpu_composed_layers.append(ele)
				if len(gpu_composed_layers) == num_of_gpu_composition:
					break

			print("penalty_table:", penalty_table)
			
			gop_idx = 0
			i = 0
			while i <= len(self.layers) - 1:
				if i in [item[0] for item in gpu_composed_layers]:
					hwc_verification_result.append(Result(self.layers[i], self.metadata[i], GOP._value2member_map_[gop_idx]))
					hwc_verification_result.append(Result(self.layers[i+1], self.metadata[i+1], GOP._value2member_map_[gop_idx]))
					print("i", i)
					i += 1
				else:
					hwc_verification_result.append(Result(self.layers[i], self.metadata[i], GOP._value2member_map_[gop_idx]))
				gop_idx += 1
				i += 1
			return True

hwc_input_layers = [
	# hdr=HDR.SDR, format=ColorFormat.HAL_PIXEL_FORMAT_RGBA_8888, is_scale_down=False, is_rotate=False
	Layer(HDR.SDR,   "rgba8888",    False, False),
	Layer(HDR.SDR,   "argb4444",    False, False),
	Layer(HDR.HDR10, "rgb565",      True,  False),
	Layer(HDR.HLG,   "bgra8888",    False, False),
	Layer(HDR.HDR10, "argb8888",    False, False),
	Layer(HDR.SDR,   "rgba1010102", False, False),
]

print("========= Input Layers ==========\n")
for input_layer in hwc_input_layers:
	print(input_layer)
	print("-> HDR/SDR:", input_layer.hdr, ' , FMT:', input_layer.format, ' , ROTATE:', input_layer.is_rotate, ' , SCALE_DOWN:', input_layer.is_scale_down, "\n")

#first round classification
hwc_verifier_metadata = []

#final round classification
hwc_verification_result = []

for layer in hwc_input_layers:
	hwc_verifier_metadata.append(Verifier(layer).verify())

template_cache = Template_Cache(hwc_input_layers, hwc_verifier_metadata)
is_hit = template_cache.is_cache_hit()
print("Template Cache:", is_hit)

if is_hit == False:
	dispatcher = Dispatcher(hwc_input_layers, hwc_verifier_metadata)
	dispatcher.dispatch()

print("========= Output OVLs ==========\n")
for result in hwc_verification_result:
	print(result.layer)
	print(result.label)
	print(result.gop)
	print("\n")
