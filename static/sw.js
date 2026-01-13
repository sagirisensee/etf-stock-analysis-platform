const CACHE_NAME = 'ai-investment-analysis-v1';
const urlsToCache = [
  '/',
  '/analysis',
  '/history',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// 安装事件 - 缓存资源
self.addEventListener('install', event => {
  console.log('Service Worker 安装中...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('缓存已打开');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        // 立即激活新的 Service Worker
        return self.skipWaiting();
      })
      .catch(error => {
        console.log('缓存安装失败:', error);
      })
  );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', event => {
  console.log('Service Worker 激活中...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('删除旧缓存:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // 立即控制所有页面
      return self.clients.claim();
    })
  );
});

// 拦截请求 - 缓存优先策略
self.addEventListener('fetch', event => {
  // 只处理GET请求
  if (event.request.method !== 'GET') {
    return;
  }

  // 跳过 chrome-extension 和其他非http(s) 请求
  if (!event.request.url.startsWith('http')) {
    return;
  }

  // API请求使用网络优先策略
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // 如果网络请求成功，缓存响应
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseClone);
              });
          }
          return response;
        })
        .catch(() => {
          // 网络失败时，尝试从缓存获取
          return caches.match(event.request);
        })
    );
    return;
  }

  // 静态资源使用缓存优先策略
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request)
          .then(response => {
            // 检查响应是否有效
            if (!response || response.status !== 200 || response.type !== 'basic') {
              // 对于跨域请求，直接返回响应
              if (response.type === 'opaque' || response.type === 'cors') {
                return response;
              }
              return response;
            }
            // 缓存响应
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            return response;
          })
          .catch(() => {
            // 对于HTML页面，返回离线页面
            if (event.request.destination === 'document') {
              return caches.match('/');
            }
            // 对于其他请求，返回空的 Response
            return new Response('', { status: 503, statusText: 'Service Unavailable' });
          });
      })
  );
});

// 监听推送通知（可选）
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/icon-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: data.primaryKey
      }
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// 监听通知点击
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});
