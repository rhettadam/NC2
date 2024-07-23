import matplotlib.pyplot as plt
import numpy as np

# Create some data
data = np.random.rand(10, 10)

# Plot using the normal colormap
plt.subplot(1, 2, 1)
plt.imshow(data, cmap='viridis')
plt.title('Normal Colormap')
plt.colorbar()

# Plot using the reversed colormap
plt.subplot(1, 2, 2)
plt.imshow(data, cmap='viridis_r')
plt.title('Reversed Colormap')
plt.colorbar()

plt.show()
