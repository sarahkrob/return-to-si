from optparse import OptionParser

class Options():
    def __init__(self):
        ###########################################################################
        # set up command line arguments using optparse library
        ###########################################################################
        usage = "usage: %prog [options] arg1 arg2"
        parser = OptionParser(usage, version="%prog 0.1")
        parser.add_option("-x", "--width", type="int", dest="width", default=600,
                          help="set window width [600]")
        parser.add_option("-y", "--height", type="int", dest="height", default=800,
                          help="set window height [800]")
        parser.add_option("-l", "--limitframe", type="float", dest="limitFrameRate",
                          help="limit framerate to specified value [NO DEFAULT]")
        parser.add_option("-d", "--debug", action="store_true", dest="debug",
                          default=False, help="enable debug print output")
        parser.add_option("-s", "--server", action="store_true", dest="server",
                          default=False, help="enable server-only run mode")
        parser.add_option("-c", "--client", action="store_true", dest="client",
                          default=False, help="enable client-only run mode")
        parser.add_option("-r", "--run", type="int", dest="runtime", default=10,
                          help="set run time [10]")
        parser.add_option("-p", "--port", type="int", dest="server_port", default="5556",
                          help="set server port [5556]")
        parser.add_option("-i", "--ipaddr", type="string", dest="ipaddr", default="localhost",
                          help="set server IP [localhost]")
        (options, args) = parser.parse_args()
        self.opts = options
