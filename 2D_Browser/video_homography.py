import cv2
import numpy as np


FLANN_INDEX_KDTREE = 1	# bug: flann enums are missing

flann_params = dict(algorithm = FLANN_INDEX_KDTREE,
					trees = 4)
					
def anorm2(a):
	return (a*a).sum(-1)
def anorm(a):
	return np.sqrt( anorm2(a) )

def match_bruteforce(desc1, desc2, r_threshold = 0.75):
	res = []
	for i in xrange(len(desc1)):
		dist = anorm( desc2 - desc1[i] )
		n1, n2 = dist.argsort()[:2]
		r = dist[n1] / dist[n2]
		if r < r_threshold:
			res.append((i, n1))
	return np.array(res)

def match_flann(desc1, desc2, r_threshold = 0.6):
	flann = cv2.flann_Index(desc2, flann_params)
	idx2, dist = flann.knnSearch(desc1, 2, params = {}) # bug: need to provide empty dict
	mask = dist[:,0] / dist[:,1] < r_threshold
	idx1 = np.arange(len(desc1))
	pairs = np.int32( zip(idx1, idx2[:,0]) )
	return pairs[mask]

def match(match_fn, desc1, desc2, kp1, kp2, r_threshold):
	"""
		Match a set of descriptors using a supplied matching method:
		Parameters:
			- match: a matching function (in this case, bruteforce and flann - see above)
			- r_threshold: radius threshold?
	"""
	# call the matching function passing descriptor vectors
	# m is a list of index values for matched keypoints
	m = match_fn(desc1, desc2, r_threshold) 
	matched_p1 = np.array([kp1[i].pt for i, j in m], np.float32) # get img1 keypoints from match index
	matched_p2 = np.array([kp2[j].pt for i, j in m], np.float32) # get img2 keypoints from match index

	H, status = cv2.findHomography(matched_p2, matched_p1, cv2.RANSAC, 5.0) # find homography matrix
	
	# status is a binary mask corresponding to points used from matched points?
	print '%d / %d	inliers/matched' % (np.sum(status), len(status))
	
	return H, status, matched_p1, matched_p2 

def draw_match_overlay(img1, img2, H):
	h1, w1 = img1.shape[:2]
	overlay = cv2.warpPerspective(img2, H, (w1,h1))
	# populate the vis array with pixel values from both images
	img_overlay = cv2.addWeighted(img1, 0.5, overlay, 0.5, 0.0)
	#vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR) # convert to color image
	return img_overlay


def homography_map(img1, img2):
	"""homography mapping of img2 onto img1
		- returns H - the homography matrix that
		allows one to transform img2 to match img1
	"""
	surf = cv2.SURF(500)
	img1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
	img2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)

	kp1, desc1 = surf.detect(img1, None, useProvidedKeypoints=False)
	kp2, desc2 = surf.detect(img2, None, useProvidedKeypoints=False)
	desc1.shape = (-1, surf.descriptorSize())
	desc2.shape = (-1, surf.descriptorSize())
	print 'img1 - %d features, img2 - %d features' % (len(kp1), len(kp2))

	H, status, p1, p2 = match(match_flann, desc1, desc2, kp1, kp2, r_threshold=0.60)

	img_overlay = draw_match_overlay(img1, img2, H)
	return np.dstack((img_overlay, img_overlay, img_overlay)), H

def undistort_point_dev(pt, K, dist_coeffs):
	# see link for reference on the equation
	# http://opencv.willowgarage.com/documentation/camera_calibration_and_3d_reconstruction.html
	x, y = pt
	k1,k2,k3 = dist_coeffs[0],dist_coeffs[1],dist_coeffs[-1]
	p1, p2 = dist_coeffs[2], dist_coeffs[3]
	r = np.sqrt(x**2 + y**2)
	x_undistort = (x * (1+ (k1*r**2) + (k2*r**4) + (k3*r**6))) + 2*p1*x*y + p2*(r**2 + 2*x**2)
	y_undistort = (y * (1+ (k1*r**2) + (k2*r**4) + (k3*r**6))) + 2*p2*y*x + p1*(r**2 + 2*y**2)

	return x_undistort[0], y_undistort[0]



def undistort_point(pt, K, dist_coeffs):
	# pt is in pixels
	# returns undistorted point in pixel coordinates


	u = pt[0]
	v = pt[1]

	u0 = K[0,2] # cx
	v0 = K[1,2] # cy
	fx = K[0,0]
	fy = K[1,1]

	_fx = 1.0/fx
	_fy = 1.0/fy
	
	k1=dist_coeffs[0]
	k2=dist_coeffs[1]
	p1=dist_coeffs[2]
	p2=dist_coeffs[3]

	y = (v - v0)*_fy
	y2 = y*y
	ky = 1 + (k1 + k2*y2)*y2
	k2y = 2*k2*y2
	_2p1y = 2*p1*y
	_3p1y2 = 3*p1*y2
	p2y2 = p2*y2

	x = (u - u0)*_fx
	x2 = x*x
	kx = (k1 + k2*x2)*x2
	d = kx + ky + k2y*x2
	

	_u = fx*(x*(d + _2p1y) + p2y2 + (3*p2)*x2) + u0
	_v = fy*(y*(d + (2*p2)*x) + _3p1y2 + p1*x2) + v0
	

	return _u[0],_v[0]














