export const markets = [
  { value: 'GB', label: '英国 / United Kingdom', name: '英国' },
  { value: 'EU', label: '欧盟 / European Union', name: '欧盟' },
  { value: 'US', label: '美国 / United States', name: '美国' },
  { value: 'CA', label: '加拿大 / Canada', name: '加拿大' },
  { value: 'AU', label: '澳大利亚 / Australia', name: '澳大利亚' },
  { value: 'CN', label: '中国大陆 / Mainland China', name: '中国大陆' },
  { value: 'JP', label: '日本 / Japan', name: '日本' },
  { value: 'KR', label: '韩国 / South Korea', name: '韩国' },
  { value: 'SG', label: '新加坡 / Singapore', name: '新加坡' },
] as const

export const productCategories = [
  { value: 'reusable_bottle', label: '日用消费品 · 水杯' },
  { value: 'household', label: '家居与日用品' },
  { value: 'electronics', label: '电子数码与家电' },
  { value: 'clothing', label: '服装、鞋履与配饰' },
  { value: 'beauty', label: '美妆与个人护理' },
  { value: 'food', label: '食品与饮料' },
  { value: 'pet_supplies', label: '宠物用品' },
  { value: 'office_supplies', label: '办公与纸品' },
  { value: 'packaging', label: '包装与容器' },
  { value: 'other', label: '其他消费品' },
] as const

export type Market = (typeof markets)[number]['value']
export type ProductCategory = (typeof productCategories)[number]['value']
export const marketName = (value: string) => markets.find((m) => m.value === value)?.name ?? value
export const categoryName = (value: string) =>
  productCategories.find((c) => c.value === value)?.label ?? value
