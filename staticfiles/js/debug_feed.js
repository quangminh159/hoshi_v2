
/**
 * Debug script để kiểm tra lỗi hiển thị feed
 */
console.log('=== DEBUG FEED ===');

// Kiểm tra xem trang feed đã được tải chưa
document.addEventListener('DOMContentLoaded', function() {
    console.log('Trang đã được tải hoàn toàn');
    
    // Kiểm tra các bài viết
    const posts = document.querySelectorAll('.post-card');
    console.log(`Số lượng bài viết hiển thị: ${posts.length}`);
    
    // Kiểm tra dữ liệu
    const feedContainer = document.getElementById('feed-container');
    if (feedContainer) {
        console.log('Feed container đã được tìm thấy');
    } else {
        console.error('Feed container không tìm thấy!');
    }
    
    // Debug các thông báo lỗi
    if (window.django_messages) {
        console.log('Django messages:', window.django_messages);
    }
    
    // Kiểm tra các ảnh
    const images = document.querySelectorAll('img');
    console.log(`Số lượng ảnh: ${images.length}`);
    
    // Kiểm tra các link bị lỗi
    for (const img of images) {
        if (!img.complete || img.naturalHeight === 0) {
            console.error(`Ảnh lỗi: ${img.src}`);
        }
    }
    
    // Thử reload và clear cache
    document.getElementById('reload-btn')?.addEventListener('click', function() {
        location.reload(true);
    });
});

// Thêm nút reload vào trang
setTimeout(function() {
    const reloadBtn = document.createElement('button');
    reloadBtn.id = 'reload-btn';
    reloadBtn.className = 'btn btn-primary position-fixed';
    reloadBtn.style.cssText = 'bottom: 20px; right: 20px; z-index: 9999;';
    reloadBtn.textContent = 'Reload Page';
    document.body.appendChild(reloadBtn);
}, 1000);
