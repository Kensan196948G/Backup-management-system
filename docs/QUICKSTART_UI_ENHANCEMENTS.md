# Quick Start Guide - Media Form UI Enhancements

## For Developers

### Files Modified
- `/app/templates/media/create.html` (50KB, 1,060 lines)

### Documentation Created
- `/MEDIA_FORM_ENHANCEMENTS.md` - Complete technical documentation
- `/docs/ui-components-guide.md` - Visual component reference
- `/docs/QUICKSTART_UI_ENHANCEMENTS.md` - This file

---

## 5 Key Enhancements

### 1️⃣ QR Code Generator
**What it does:** Auto-generates QR code as user types Media ID
**Key elements:**
- `#qr-preview` - Main QR display
- `#download-qr` - Download button
- `#print-qr` - Print button
- **Library:** QRCode.js (CDN loaded)

**Test it:**
```javascript
document.getElementById('media_id').value = 'LTO-123456';
```

---

### 2️⃣ Capacity Calculator
**What it does:** Visual capacity selector with GB/TB converter
**Key elements:**
- `#capacity_value` - Numeric input
- `#capacity_unit` - Unit selector (GB/TB)
- `#capacity_slider` - Range slider
- `#capacity_indicator` - Visual bar

**Test it:**
```javascript
document.getElementById('capacity_value').value = 5;
document.getElementById('capacity_unit').value = 'tb';
```

---

### 3️⃣ Location Picker
**What it does:** Interactive 3-level location selector with visual map
**Key elements:**
- `#building_select` - Building dropdown
- `#floor_select` - Floor dropdown
- `#rack_select` - Rack dropdown
- `#rack_grid` - Visual rack map

**Test it:**
```javascript
document.getElementById('building_select').value = '本社ビル';
document.getElementById('building_select').dispatchEvent(new Event('change'));
```

---

### 4️⃣ Media Type Wizard
**What it does:** Shows type-specific fields based on media type
**Key elements:**
- `#tape_fields` - Tape-specific (LTO generation, compression)
- `#disk_fields` - Disk-specific (RPM, interface)
- `#optical_fields` - Optical-specific (write speed)
- `#cloud_fields` - Cloud-specific (provider, region)

**Test it:**
```javascript
document.getElementById('media_type').value = 'tape';
document.getElementById('media_type').dispatchEvent(new Event('change'));
```

---

### 5️⃣ Live Preview Card
**What it does:** Real-time media label preview with mini QR code
**Key elements:**
- `#label-preview-id` - Media ID
- `#label-preview-name` - Label name
- `#preview-qr-small` - Mini QR code (80×80px)
- `.media-preview-card` - Container

**Updates automatically** when any field changes.

---

## JavaScript Functions Reference

### Main Functions
```javascript
generateQRCode(text)           // Creates QR code from text
updateCapacity()               // Syncs capacity inputs
showRackMap(building, floor)   // Displays visual rack grid
updateRackMapSelection(rack)   // Highlights selected rack
```

### Event Listeners
- `media_id` input → Generate QR + update preview
- `capacity_value` input → Update slider + bar
- `media_type` change → Show/hide wizard fields
- `building_select` change → Populate floor dropdown
- `floor_select` change → Populate rack dropdown + show map
- `rack_select` change → Update location field

---

## CSS Classes Reference

### Custom Classes
```css
.qr-preview           /* QR code display area */
.qr-actions           /* Download/print buttons */
.capacity-bar         /* Visual capacity bar */
.capacity-indicator   /* Moving indicator */
.location-map         /* Rack map container */
.rack-grid            /* Grid layout for racks */
.rack-slot            /* Individual rack slot */
.rack-slot.selected   /* Selected rack (blue) */
.rack-slot.occupied   /* Occupied rack (red) */
.type-specific-fields /* Hidden by default */
.type-specific-fields.show /* Visible with animation */
.media-preview-card   /* Label preview */
```

---

## Data Structures

### Location Data
```javascript
const locationData = {
  '本社ビル': {
    floors: ['1F', '2F', '3F', 'B1F'],
    racks: {
      '1F': ['R1', 'R2', 'R3', 'R4'],
      // ...
    }
  },
  // ... more buildings
};
```

### Media Type Map
```javascript
const typeMap = {
  'tape': 'テープ (LTO)',
  'disk': 'ディスク (HDD/SSD)',
  'optical': '光学メディア',
  'cloud': 'クラウドストレージ'
};
```

---

## Backend Integration

### Form Submission
The form submits to: `{{ url_for('media.create') }}`

### Expected POST Data
```python
{
  # Basic fields (existing)
  'media_id': 'LTO-123456',
  'label_name': '営業部バックアップ用',
  'media_type': 'tape',
  'capacity_gb': 12288,  # Always in GB
  'location': '本社ビル-1F-R1',
  'status': 'available',

  # Type-specific fields (new, optional)
  'tape_type': 'lto',
  'lto_generation': 'lto-8',
  'write_count': 0,
  'tape_compression': 'hardware',

  # OR for disk:
  'interface_type': 'sas',
  'rpm': '7200',
  'form_factor': '3.5',
  'raid_support': 'yes',

  # OR for cloud:
  'cloud_provider': 'aws-s3',
  'storage_class': 'glacier',
  'region': 'ap-northeast-1',
  'bucket_name': 'backup-storage-prod',

  # ... etc
}
```

**Note:** Type-specific fields only submit if media type is selected.

---

## Customization Guide

### Add New Building/Location
Edit location data in JavaScript:
```javascript
const locationData = {
  // ... existing buildings
  '新しいビル': {
    floors: ['1F', '2F'],
    racks: {
      '1F': ['R1', 'R2', 'R3'],
      '2F': ['R1', 'R2']
    }
  }
};
```

### Add New Media Type
1. Add option to `#media_type` select:
```html
<option value="nvme">NVMe SSD</option>
```

2. Create type-specific fields section:
```html
<div id="nvme_fields" class="type-specific-fields">
  <!-- Your custom fields here -->
</div>
```

3. Update JavaScript field map:
```javascript
const fieldMap = {
  // ... existing
  'nvme': 'nvme_fields'
};
```

### Change Capacity Range
Modify slider max value:
```html
<input type="range" id="capacity_slider"
       min="0" max="40000" step="100">  <!-- Changed to 40TB -->
```

Update visual bar calculation:
```javascript
const percentage = Math.min((capacityGB / 40960) * 100, 100);
```

---

## Common Issues & Solutions

### QR Code Not Generating
**Problem:** QRCode.js library not loaded
**Solution:** Check CDN link in template:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
```

### Capacity Bar Not Updating
**Problem:** Event listener not attached
**Solution:** Ensure `updateCapacity()` is called:
```javascript
document.getElementById('capacity_value').addEventListener('input', updateCapacity);
```

### Location Map Not Showing
**Problem:** Floor/building mismatch in data structure
**Solution:** Verify `locationData` has correct building/floor keys

### Type-Specific Fields Not Showing
**Problem:** CSS class not applied
**Solution:** Check media type value matches fieldMap:
```javascript
console.log(document.getElementById('media_type').value);
// Should match key in fieldMap
```

---

## Testing Commands

### Browser Console Tests
```javascript
// Test all components at once
document.getElementById('media_id').value = 'LTO-TEST';
document.getElementById('label_name').value = 'テストメディア';
document.getElementById('media_type').value = 'tape';
document.getElementById('media_type').dispatchEvent(new Event('change'));
document.getElementById('capacity_value').value = 12;
document.getElementById('capacity_unit').value = 'tb';
document.getElementById('building_select').value = 'データセンター';
document.getElementById('building_select').dispatchEvent(new Event('change'));
```

### Check if QR Code Library Loaded
```javascript
console.log(typeof QRCode); // Should output "function"
```

### Verify Form Data Before Submit
```javascript
const formData = new FormData(document.getElementById('media-form'));
for (let [key, value] of formData.entries()) {
  console.log(key + ': ' + value);
}
```

---

## Performance Optimization Tips

### QR Code Generation
- Debounce input if generating large batches
- Cache QR code if Media ID doesn't change

### Location Map Rendering
- Use document fragment for bulk DOM insertion
- Lazy load rack data via AJAX if very large

### Capacity Slider
- Use `requestAnimationFrame` for smooth animations
- Throttle slider input events

---

## Browser Support

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Fully supported |
| Firefox | 88+ | ✅ Fully supported |
| Safari | 14+ | ✅ Fully supported |
| Edge | 90+ | ✅ Fully supported |
| IE 11 | - | ❌ Not supported |

**Required Features:**
- ES6 JavaScript
- Canvas API
- CSS Grid
- Flexbox
- HTML5 Form Validation

---

## Next Steps

1. **Test the Form:**
   - Open `/media/create` in browser
   - Try each feature
   - Submit test data

2. **Backend Updates (if needed):**
   - Add database fields for type-specific data
   - Update form handler to accept new fields
   - Add validation for optional fields

3. **Enhancements:**
   - Add AJAX Media ID uniqueness check
   - Implement real-time rack availability from API
   - Add barcode generation alongside QR codes
   - Create bulk import feature

---

## Getting Help

### Documentation
- Full technical docs: `/MEDIA_FORM_ENHANCEMENTS.md`
- Visual guide: `/docs/ui-components-guide.md`
- This quickstart: `/docs/QUICKSTART_UI_ENHANCEMENTS.md`

### Debug Mode
Add to console to enable verbose logging:
```javascript
// Add at top of script section
const DEBUG = true;
function log(...args) {
  if (DEBUG) console.log('[MediaForm]', ...args);
}
```

---

**Quick Start Guide Version:** 1.0.0
**Created:** November 2, 2025
**Author:** Agent-06 (UI/UX Specialist)

**Ready to use!** 🚀
