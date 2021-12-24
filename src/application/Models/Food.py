# Clara

class Food:
    def __init__(self, image, name, description, price, allergy,
                 specification=None):
        self.__image = image
        self.name = name
        self.description = description
        self.price = price
        self.allergy = allergy
        self.specification = specification

    # Get the image as a file?
    def get_image(self):
        return self.__image

    # Set the image as a file?
    def set_image(self, image):
        self.__image = image
