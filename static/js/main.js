// 主要JavaScript逻辑文件
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initMobileMenu();
    initScrollAnimations();
    initStatsCounters();
    initSmoothScrolling();
    initParallaxEffect();
    
    console.log('资金分析平台已加载完成');
});

// 移动端菜单功能
function initMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
        
        // 点击菜单项后关闭菜单
        const menuLinks = mobileMenu.querySelectorAll('a');
        menuLinks.forEach(link => {
            link.addEventListener('click', function() {
                mobileMenu.classList.add('hidden');
            });
        });
    }
}

// 滚动动画
function initScrollAnimations() {
    // 创建Intersection Observer
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                
                // 根据元素类型应用不同的动画
                if (element.classList.contains('card-hover')) {
                    anime({
                        targets: element,
                        translateY: [50, 0],
                        opacity: [0, 1],
                        duration: 800,
                        easing: 'easeOutQuart',
                        delay: Math.random() * 200
                    });
                } else if (element.classList.contains('feature-icon')) {
                    anime({
                        targets: element,
                        scale: [0, 1],
                        rotate: [180, 0],
                        duration: 1000,
                        easing: 'easeOutElastic(1, .8)'
                    });
                } else {
                    anime({
                        targets: element,
                        translateY: [30, 0],
                        opacity: [0, 1],
                        duration: 600,
                        easing: 'easeOutQuart'
                    });
                }
                
                observer.unobserve(element);
            }
        });
    }, observerOptions);
    
    // 观察所有需要动画的元素
    const animatedElements = document.querySelectorAll('.card-hover, .feature-icon, .glass-effect');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        observer.observe(el);
    });
}

// 统计数字计数器动画
function initStatsCounters() {
    const counters = document.querySelectorAll('.stats-counter');
    
    const countUp = (element, target) => {
        const duration = 2000;
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            
            // 格式化处理
            if (target >= 1000) {
                element.textContent = Math.floor(current).toLocaleString();
            } else if (target < 10) {
                element.textContent = current.toFixed(1);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    };
    
    // 使用Intersection Observer触发动画
    const counterObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseFloat(counter.getAttribute('data-target'));
                countUp(counter, target);
                counterObserver.unobserve(counter);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => {
        counterObserver.observe(counter);
    });
}

// 平滑滚动
function initSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                const offsetTop = targetElement.offsetTop - 80; // 考虑导航栏高度
                
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// 视差滚动效果
function initParallaxEffect() {
    let ticking = false;
    
    function updateParallax() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.hero-bg');
        
        parallaxElements.forEach(element => {
            const speed = 0.5;
            const yPos = -(scrolled * speed);
            element.style.transform = `translateY(${yPos}px)`;
        });
        
        ticking = false;
    }
    
    function requestTick() {
        if (!ticking) {
            requestAnimationFrame(updateParallax);
            ticking = true;
        }
    }
    
    window.addEventListener('scroll', requestTick);
}

// 导航栏滚动效果
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('nav');
    if (window.scrollY > 100) {
        navbar.style.background = 'rgba(15, 20, 25, 0.95)';
        navbar.style.backdropFilter = 'blur(20px)';
    } else {
        navbar.style.background = 'rgba(26, 35, 50, 0.8)';
        navbar.style.backdropFilter = 'blur(10px)';
    }
});

// 卡片悬停效果增强
document.querySelectorAll('.card-hover').forEach(card => {
    card.addEventListener('mouseenter', function() {
        anime({
            targets: this,
            scale: 1.02,
            translateY: -8,
            duration: 300,
            easing: 'easeOutQuart'
        });
    });
    
    card.addEventListener('mouseleave', function() {
        anime({
            targets: this,
            scale: 1,
            translateY: 0,
            duration: 300,
            easing: 'easeOutQuart'
        });
    });
});

// 按钮点击效果
document.querySelectorAll('button').forEach(button => {
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            pointer-events: none;
        `;
        
        this.style.position = 'relative';
        this.style.overflow = 'hidden';
        this.appendChild(ripple);
        
        anime({
            targets: ripple,
            scale: [0, 2],
            opacity: [1, 0],
            duration: 600,
            easing: 'easeOutQuart',
            complete: () => ripple.remove()
        });
    });
});

// 页面加载完成后的欢迎动画
window.addEventListener('load', function() {
    // Hero区域标题动画
    anime({
        targets: '.gradient-text',
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 1000,
        easing: 'easeOutElastic(1, .8)',
        delay: 500
    });
    
    // 导航栏动画
    anime({
        targets: 'nav',
        translateY: [-100, 0],
        opacity: [0, 1],
        duration: 800,
        easing: 'easeOutQuart'
    });
});

// 错误处理
window.addEventListener('error', function(e) {
    console.error('页面错误:', e.error);
});

// 性能监控
if ('performance' in window) {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log('页面加载性能:', {
                loadTime: perfData.loadEventEnd - perfData.loadEventStart,
                domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                totalTime: perfData.loadEventEnd - perfData.fetchStart
            });
        }, 0);
    });
}

// 导出主要函数供其他模块使用
window.FundAnalysisPlatform = {
    initMobileMenu,
    initScrollAnimations,
    initStatsCounters,
    initSmoothScrolling,
    initParallaxEffect
};