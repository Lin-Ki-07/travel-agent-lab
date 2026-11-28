// 独立的外链照片目录；不发起请求、不保存图片、不推断地点匹配。
export interface PlacePhoto {
  imageUrl: string
  sourcePageUrl: string
  author: string
  license: string
  licenseUrl: string
}

export interface PlacePhotoBinding {
  placeSource: string
  placeId: string
  photos: PlacePhoto[]
}

function isHttpsUrl(value: unknown): value is string {
  if (typeof value !== 'string' || value !== value.trim()) return false
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && !url.username && !url.password
  } catch {
    return false
  }
}

function isPhoto(value: unknown): value is PlacePhoto {
  if (!value || typeof value !== 'object') return false
  const photo = value as Record<string, unknown>
  return isHttpsUrl(photo.imageUrl) && isHttpsUrl(photo.sourcePageUrl) &&
    isHttpsUrl(photo.licenseUrl) &&
    typeof photo.author === 'string' && photo.author.trim().length > 0 &&
    typeof photo.license === 'string' && photo.license.trim().length > 0
}

// 目录必须来自已人工审核的来源；HTTPS校验不代表来源许可或图片可用性。
// 使用来源+ID精确绑定，不按名称猜测，不把未知数据绑定到现有行程。
export function getPlacePhotos(
  place: { source: string; place_id: string },
  bindings: readonly PlacePhotoBinding[] = [],
): PlacePhoto[] {
  if (!place.source.trim() || !place.place_id.trim()) return []
  const matches = bindings.filter((binding) =>
    binding.placeSource === place.source && binding.placeId === place.place_id)
  // 重复绑定视为有歧义，避免隐式选用其中一份。
  if (matches.length !== 1 || !Array.isArray(matches[0].photos)) return []
  const seen = new Set<string>()
  const result: PlacePhoto[] = []
  for (const photo of matches[0].photos) {
    if (!isPhoto(photo) || seen.has(photo.imageUrl)) continue
    seen.add(photo.imageUrl)
    result.push({
      imageUrl: photo.imageUrl, sourcePageUrl: photo.sourcePageUrl,
      author: photo.author, license: photo.license, licenseUrl: photo.licenseUrl,
    })
    if (result.length === 3) break
  }
  return result
}
