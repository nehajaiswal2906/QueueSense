# QueueSense - Video Media Attribution & Licence Details

This document records the provenance, licensing, and usage rights for video assets integrated into QueueSense for demonstration and evaluation.

---

## 1. Primary Demonstration Video: `assets/canteen_queue_demo.mp4`

- **Title**: Busy Supermarket Checkout & Counter Queue in Auckland
- **Source Platform**: [Pexels](https://www.pexels.com/)
- **Source URL**: [https://www.pexels.com/video/busy-supermarket-checkout-in-auckland-39221981/](https://www.pexels.com/video/busy-supermarket-checkout-in-auckland-39221981/)
- **Direct Stream**: `https://videos.pexels.com/video-files/39221981/16690547_1280_720_25fps.mp4`
- **Licence**: [Pexels License](https://www.pexels.com/license/)
  - Free for personal and commercial use.
  - Attribution is not legally required, but gratefully provided.
  - Modifications and redistributions within software projects permitted.
- **Download Date**: October 2026
- **Technical Specifications**:
  - **Resolution**: 1280 × 720 (HD 720p)
  - **Framerate**: 25.0 FPS
  - **Total Frames**: 484 (~19.36 seconds duration)
  - **Filesize**: ~4.46 MB (GitHub-friendly, under 25 MB threshold)
- **Suitability & Selection Rationale**:
  - **Stationary Camera**: Fixed tripod/counter perspective ideal for stationary Region of Interest (ROI) monitoring.
  - **Multiple Concurrent People**: 8–11 concurrent tracked people per frame.
  - **Clear Queue Geometry**: Multiple customers queuing in checkout lanes with carts/baskets.
  - **Real Service Events**: Customers dwell in queue, approach the cashier counter, complete transactions, and exit through the left walkway, enabling empirical service-rate and queue-count tracking.

---

## 2. Secondary Reference Video: `assets/cafe_counter_candidate.mp4`

- **Title**: Busy Cafe with Customers Ordering at Counter
- **Source Platform**: [Pexels](https://www.pexels.com/)
- **Source URL**: [https://www.pexels.com/video/busy-cafe-with-customers-ordering-at-counter-35545660/](https://www.pexels.com/video/busy-cafe-with-customers-ordering-at-counter-35545660/)
- **Direct Stream**: `https://videos.pexels.com/video-files/35545660/15059167_1280_720_30fps.mp4`
- **Licence**: [Pexels License](https://www.pexels.com/license/)
  - Free for personal and commercial use.
- **Download Date**: October 2026
- **Technical Specifications**:
  - **Resolution**: 1280 × 720 (HD 720p)
  - **Framerate**: 29.97 FPS
  - **Total Frames**: 308 (~10.28 seconds duration)
  - **Filesize**: ~7.23 MB
- **Evaluation Notes**:
  - Examined per user recommendation.
  - Frames 0–120 clearly capture a customer ordering at the beverage service counter ("İÇECEKLER" counter) with dining visitors.
  - Frames 121–308 feature dynamic camera panning forward and left towards the dessert counter ("TATLI"), causing fixed ROI perspective shift. Retained as secondary benchmark for camera motion stress testing.

---

## Compliance Notice

Both video assets were obtained directly through authorized public content distribution mechanisms in strict adherence to source platform terms of service. No private, confidential, or surveillance feeds are used.
