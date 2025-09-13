/**
 * Teacher Shopping Assistant - Frontend JavaScript
 * Handles camera functionality, image upload, and API communication
 */

let currentStream = null;
let capturedImageData = null;

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Teacher Shopping Assistant initialized');
    
    // Set up file input change handler
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.addEventListener('change', handleFileUpload);
    }
    
    // Set up drag and drop functionality
    const uploadArea = document.getElementById('uploadArea');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
        uploadArea.addEventListener('click', openFileUpload);
    }
});

/**
 * Open camera modal
 */
function openCamera() {
    console.log('📷 Opening camera...');
    const modal = new bootstrap.Modal(document.getElementById('cameraModal'));
    modal.show();
    
    // Start camera when modal is shown
    document.getElementById('cameraModal').addEventListener('shown.bs.modal', startCamera);
    document.getElementById('cameraModal').addEventListener('hidden.bs.modal', stopCamera);
}

/**
 * Start camera stream
 */
async function startCamera() {
    try {
        console.log('🎥 Starting camera stream...');
        
        const video = document.getElementById('cameraVideo');
        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment' // Use back camera on mobile
            }
        };
        
        currentStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = currentStream;
        
        console.log('✅ Camera started successfully');
        
    } catch (error) {
        console.error('❌ Error starting camera:', error);
        alert('Unable to access camera. Please check permissions and try again.');
    }
}

/**
 * Stop camera stream
 */
function stopCamera() {
    if (currentStream) {
        console.log('🛑 Stopping camera stream...');
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
        
        const video = document.getElementById('cameraVideo');
        video.srcObject = null;
    }
}

/**
 * Capture photo from camera
 */
function capturePhoto() {
    try {
        console.log('📸 Capturing photo...');
        
        const video = document.getElementById('cameraVideo');
        const canvas = document.getElementById('cameraCanvas');
        const capturedImage = document.getElementById('capturedImage');
        const capturedImageContainer = document.getElementById('capturedImageContainer');
        
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to data URL
        capturedImageData = canvas.toDataURL('image/jpeg', 0.8);
        capturedImage.src = capturedImageData;
        
        // Show captured image and hide video
        video.style.display = 'none';
        capturedImageContainer.classList.remove('d-none');
        
        // Update button states
        document.getElementById('captureBtn').style.display = 'none';
        document.getElementById('retakeBtn').style.display = 'inline-block';
        document.getElementById('usePhotoBtn').style.display = 'inline-block';
        
        console.log('✅ Photo captured successfully');
        
    } catch (error) {
        console.error('❌ Error capturing photo:', error);
        alert('Error capturing photo. Please try again.');
    }
}

/**
 * Retake photo
 */
function retakePhoto() {
    console.log('🔄 Retaking photo...');
    
    const video = document.getElementById('cameraVideo');
    const capturedImageContainer = document.getElementById('capturedImageContainer');
    
    // Show video and hide captured image
    video.style.display = 'block';
    capturedImageContainer.classList.add('d-none');
    
    // Update button states
    document.getElementById('captureBtn').style.display = 'inline-block';
    document.getElementById('retakeBtn').style.display = 'none';
    document.getElementById('usePhotoBtn').style.display = 'none';
    
    capturedImageData = null;
}

/**
 * Use captured photo
 */
function useCapturedPhoto() {
    if (!capturedImageData) {
        alert('No photo captured. Please take a photo first.');
        return;
    }
    
    console.log('✅ Using captured photo...');
    
    // Close camera modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('cameraModal'));
    modal.hide();
    
    // Process the image
    processImage(capturedImageData);
}

/**
 * Open file upload dialog
 */
function openFileUpload() {
    console.log('📁 Opening file upload...');
    document.getElementById('imageInput').click();
}

/**
 * Handle file upload
 */
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    console.log('📁 File selected:', file.name);
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file.');
        return;
    }
    
    // Validate file size (16MB max)
    if (file.size > 16 * 1024 * 1024) {
        alert('File size must be less than 16MB.');
        return;
    }
    
    // Read file and process
    const reader = new FileReader();
    reader.onload = function(e) {
        processImage(e.target.result);
    };
    reader.readAsDataURL(file);
}

/**
 * Handle drag over
 */
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

/**
 * Handle drag leave
 */
function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
}

/**
 * Handle file drop
 */
function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.type.startsWith('image/')) {
            console.log('📁 File dropped:', file.name);
            
            // Validate file size
            if (file.size > 16 * 1024 * 1024) {
                alert('File size must be less than 16MB.');
                return;
            }
            
            // Read file and process
            const reader = new FileReader();
            reader.onload = function(e) {
                processImage(e.target.result);
            };
            reader.readAsDataURL(file);
        } else {
            alert('Please drop an image file.');
        }
    }
}

/**
 * Process uploaded/captured image
 */
async function processImage(imageData) {
    try {
        console.log('🔄 Processing image...');
        
        // Show processing section
        showSection('processing-section');
        
        // Convert data URL to blob for upload
        const response = await fetch(imageData);
        const blob = await response.blob();
        
        // Create form data
        const formData = new FormData();
        formData.append('image', blob, 'image.jpg');
        
        // Send to server
        console.log('📤 Sending image to server...');
        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        console.log('📡 Upload response status:', uploadResponse.status);
        
        if (!uploadResponse.ok) {
            const errorText = await uploadResponse.text();
            console.error('❌ Server error response:', errorText);
            throw new Error(`Server error: ${uploadResponse.status} - ${errorText}`);
        }
        
        const result = await uploadResponse.json();
        console.log('📥 Received response:', result);
        
        if (result.success) {
            displayResults(result);
        } else {
            console.error('❌ Server returned error:', result.error);
            throw new Error(result.error || 'Unknown error');
        }
        
    } catch (error) {
        console.error('❌ Error processing image:', error);
        alert('Error processing image: ' + error.message);
        showSection('upload-section');
    }
}

/**
 * Display identification results
 */
function displayResults(result) {
    console.log('📊 Displaying results...');
    
    // Show preview image
    const previewImage = document.getElementById('previewImage');
    previewImage.src = result.image_data;
    
    // Display identification results
    const resultsContainer = document.getElementById('identificationResults');
    const identification = result.identification;
    
    let html = '';
    
    if (identification.identified_item === 'Not Found') {
        html = `
            <div class="identification-item not-found">
                <strong>Item Not Identified</strong><br>
                <small>${identification.notes || 'Could not identify the item in the image.'}</small>
            </div>
        `;
    } else {
        // Item identified successfully
        const confidenceClass = `confidence-${identification.confidence.toLowerCase()}`;
        
        html = `
            <div class="identification-item">
                <strong>Identified Item:</strong> ${identification.identified_item}<br>
                <strong>Type:</strong> ${identification.item_type}<br>
                <strong>Confidence:</strong> <span class="${confidenceClass}">${identification.confidence}</span><br>
                ${identification.key_features.length > 0 ? `<strong>Key Features:</strong> ${identification.key_features.join(', ')}<br>` : ''}
                ${identification.notes ? `<small class="text-muted">${identification.notes}</small>` : ''}
            </div>
        `;
        
        // Show shop button if product URL is available
        const shopButton = document.getElementById('shopButton');
        if (result.product_url) {
            shopButton.style.display = 'inline-block';
            shopButton.onclick = () => goToShop(result.product_url);
        } else {
            shopButton.style.display = 'none';
        }
    }
    
    resultsContainer.innerHTML = html;
    
    // Show results section
    showSection('results-section');
}

/**
 * Show specific section and hide others
 */
function showSection(sectionId) {
    const sections = ['upload-section', 'processing-section', 'results-section'];
    
    sections.forEach(id => {
        const section = document.getElementById(id);
        if (id === sectionId) {
            section.classList.remove('d-none');
        } else {
            section.classList.add('d-none');
        }
    });
}

/**
 * Go to shop (Bio-Link Depot)
 */
function goToShop(productUrl) {
    if (productUrl) {
        console.log('🛒 Opening shop URL:', productUrl);
        window.open(productUrl, '_blank');
    } else {
        console.log('🛒 Opening Bio-Link Depot homepage');
        window.open('https://www.shopbiolinkdepot.org/', '_blank');
    }
}

/**
 * Reset app to initial state
 */
function resetApp() {
    console.log('🔄 Resetting app...');
    
    // Clear any captured image data
    capturedImageData = null;
    
    // Reset file input
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.value = '';
    }
    
    // Show upload section
    showSection('upload-section');
    
    // Hide shop button
    const shopButton = document.getElementById('shopButton');
    shopButton.style.display = 'none';
}

// Global functions for HTML onclick handlers
window.openCamera = openCamera;
window.openFileUpload = openFileUpload;
window.capturePhoto = capturePhoto;
window.retakePhoto = retakePhoto;
window.useCapturedPhoto = useCapturedPhoto;
window.goToShop = goToShop;
window.resetApp = resetApp;