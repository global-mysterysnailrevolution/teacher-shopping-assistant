// Teacher Shopping Assistant JavaScript

let currentProductUrl = null;
let currentStream = null;
let capturedImageData = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('imageInput');
    
    // File input change handler
    imageInput.addEventListener('change', handleFileSelect);
    
    // Check for camera support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('Camera not supported on this device');
        // Hide camera button if not supported
        const cameraBtn = document.querySelector('button[onclick="openCamera()"]');
        if (cameraBtn) {
            cameraBtn.style.display = 'none';
        }
    }
});

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        processImage(file);
    }
}

// Camera functions
function openCamera() {
    const modal = new bootstrap.Modal(document.getElementById('cameraModal'));
    modal.show();
    
    // Request camera access
    navigator.mediaDevices.getUserMedia({ 
        video: { 
            facingMode: 'environment', // Use back camera on mobile
            width: { ideal: 1280 },
            height: { ideal: 720 }
        } 
    })
    .then(stream => {
        currentStream = stream;
        const video = document.getElementById('cameraVideo');
        video.srcObject = stream;
        
        // Show capture button
        document.getElementById('captureBtn').style.display = 'inline-block';
        document.getElementById('usePhotoBtn').style.display = 'none';
        document.getElementById('retakeBtn').style.display = 'none';
        
        // Show video, hide captured image
        document.getElementById('cameraContainer').classList.remove('d-none');
        document.getElementById('capturedImageContainer').classList.add('d-none');
    })
    .catch(error => {
        console.error('Error accessing camera:', error);
        alert('Unable to access camera. Please check permissions or use file upload instead.');
        modal.hide();
    });
}

function capturePhoto() {
    const video = document.getElementById('cameraVideo');
    const canvas = document.getElementById('cameraCanvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to blob
    canvas.toBlob(blob => {
        if (blob) {
            // Convert blob to base64 for display
            const reader = new FileReader();
            reader.onload = function(e) {
                capturedImageData = e.target.result;
                document.getElementById('capturedImage').src = capturedImageData;
                
                // Show captured image, hide video
                document.getElementById('cameraContainer').classList.add('d-none');
                document.getElementById('capturedImageContainer').classList.remove('d-none');
                
                // Update buttons
                document.getElementById('captureBtn').style.display = 'none';
                document.getElementById('usePhotoBtn').style.display = 'inline-block';
                document.getElementById('retakeBtn').style.display = 'inline-block';
            };
            reader.readAsDataURL(blob);
        }
    }, 'image/jpeg', 0.8);
}

function retakePhoto() {
    // Show video, hide captured image
    document.getElementById('cameraContainer').classList.remove('d-none');
    document.getElementById('capturedImageContainer').classList.add('d-none');
    
    // Update buttons
    document.getElementById('captureBtn').style.display = 'inline-block';
    document.getElementById('usePhotoBtn').style.display = 'none';
    document.getElementById('retakeBtn').style.display = 'none';
}

function useCapturedPhoto() {
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('cameraModal'));
    modal.hide();
    
    // Stop camera stream
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
    
    // Convert base64 to blob and process
    if (capturedImageData) {
        fetch(capturedImageData)
            .then(res => res.blob())
            .then(blob => {
                processImage(blob);
            });
    }
}

function openFileUpload() {
    document.getElementById('imageInput').click();
}

// Clean up camera when modal is closed
document.getElementById('cameraModal').addEventListener('hidden.bs.modal', function() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
});

function processImage(file) {
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
    
    // Show processing section
    showSection('processing-section');
    
    // Create FormData
    const formData = new FormData();
    formData.append('image', file);
    
    // Send to server
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayResults(data);
        } else {
            showError(data.error || 'An error occurred while processing the image.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Network error. Please try again.');
    });
}

function displayResults(data) {
    const { identification, product_url, image_data } = data;
    
    // Store product URL for later use
    currentProductUrl = product_url;
    
    // Show image preview
    document.getElementById('previewImage').src = image_data;
    
    // Display identification results
    const resultsContainer = document.getElementById('identificationResults');
    resultsContainer.innerHTML = '';
    
    // Item identification
    const itemDiv = document.createElement('div');
    itemDiv.className = 'identification-item';
    
    if (identification.identified_item === 'Not Found') {
        itemDiv.classList.add('not-found');
        itemDiv.innerHTML = `
            <strong>Item:</strong> <span class="text-danger">Not Found</span><br>
            <strong>Type:</strong> ${identification.item_type}<br>
            <strong>Notes:</strong> ${identification.notes}
        `;
    } else {
        itemDiv.innerHTML = `
            <strong>Item:</strong> ${identification.identified_item}<br>
            <strong>Confidence:</strong> <span class="confidence-${identification.confidence.toLowerCase()}">${identification.confidence}</span><br>
            <strong>Type:</strong> ${identification.item_type}<br>
            <strong>Key Features:</strong>
            <ul class="feature-list">
                ${identification.key_features.map(feature => `<li>${feature}</li>`).join('')}
            </ul>
            <strong>Notes:</strong> ${identification.notes}
        `;
    }
    
    resultsContainer.appendChild(itemDiv);
    
    // Show/hide shop button
    const shopButton = document.getElementById('shopButton');
    if (product_url) {
        shopButton.style.display = 'inline-block';
    } else {
        shopButton.style.display = 'none';
    }
    
    // Show results section
    showSection('results-section');
}

function showError(message) {
    const resultsContainer = document.getElementById('identificationResults');
    resultsContainer.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
        </div>
    `;
    
    // Show image preview if available
    const imageInput = document.getElementById('imageInput');
    if (imageInput.files.length > 0) {
        const file = imageInput.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('previewImage').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
    
    showSection('results-section');
}

function goToShop() {
    if (currentProductUrl) {
        window.open(currentProductUrl, '_blank');
    }
}

function resetApp() {
    // Reset form
    document.getElementById('imageInput').value = '';
    currentProductUrl = null;
    
    // Show upload section
    showSection('upload-section');
}

function showSection(sectionId) {
    // Hide all sections
    const sections = ['upload-section', 'processing-section', 'results-section'];
    sections.forEach(id => {
        document.getElementById(id).classList.add('d-none');
    });
    
    // Show target section
    document.getElementById(sectionId).classList.remove('d-none');
}

// Add some visual feedback for better UX
function addLoadingText() {
    const processingText = document.querySelector('#processing-section p');
    if (processingText) {
        processingText.classList.add('loading-dots');
    }
}

// Remove loading text when processing is done
function removeLoadingText() {
    const processingText = document.querySelector('#processing-section p');
    if (processingText) {
        processingText.classList.remove('loading-dots');
    }
}
