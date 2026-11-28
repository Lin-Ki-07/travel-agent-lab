import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getPlacePhotos } from '../src/placePhotos.ts'

const place = { source: 'fixture', place_id: 'zhanqiao-sample' }
// 元数据样例，不请求图片，也不绑定真实业务POI。
const photo = {
  imageUrl: 'https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/20240729_Zhanqiao_01.jpg&width=320',
  sourcePageUrl: 'https://commons.wikimedia.org/wiki/File:20240729_Zhanqiao_01.jpg',
  author: 'Windmemories', license: 'CC BY-SA 4.0',
  licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0/',
}
const binding = (photos = [photo]) => ({ placeSource: place.source, placeId: place.place_id, photos })

test('旧地点无照片合法，来源和ID必须同时精确匹配，重复绑定不猜测', () => {
  assert.deepEqual(getPlacePhotos(place), [])
  assert.deepEqual(getPlacePhotos(place, [binding([])]), [])
  assert.deepEqual(getPlacePhotos({ ...place, source: 'amap' }, [binding()]), [])
  assert.deepEqual(getPlacePhotos({ ...place, place_id: 'other' }, [binding()]), [])
  assert.deepEqual(getPlacePhotos(place, [binding(), binding()]), [])
  assert.deepEqual(getPlacePhotos(place, [binding()]), [photo])
})

test('无效链接及缺少署名许可的照片被拒绝，后续有效照片仍保留', () => {
  const invalid = [null, {}, ...['imageUrl', 'sourcePageUrl', 'licenseUrl'].flatMap((key) =>
    ['http://example.org/a', 'javascript:alert(1)', 'data:image/png;base64,a',
      '/local.jpg', 'https://user:secret@example.org/a', 'not-a-url'].map((url) => ({ ...photo, [key]: url }))),
    { ...photo, author: ' ' }, { ...photo, license: '' }]
  assert.deepEqual(getPlacePhotos(place, [binding([...invalid, photo])]), [photo])
})

test('最多三张有效且不重复的照片，顺序稳定，不修改输入', () => {
  const photos = [photo, { ...photo }, ...[2, 3, 4].map((i) => ({ ...photo, imageUrl: `https://example.org/${i}.jpg` }))]
  const catalog = [binding(photos)]
  const original = structuredClone(catalog)
  const result = getPlacePhotos(place, catalog)
  assert.deepEqual(result.map((p) => p.imageUrl), [photo.imageUrl, 'https://example.org/2.jpg', 'https://example.org/3.jpg'])
  result[0].author = 'changed'
  assert.deepEqual(catalog, original)
})
