# MIT License
#
# Copyright (c) 2020 Brett Graves
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Contrls the API functions, used for almost every feature of the library.

- Auth-less request,
	* (market clock, etc)
	* should be a class method

- Auth-ed request
	* get information
	* submit order
	* etc
	* should be object method


- Rate limits
	* 40 per minute, order submission (including submit, modify, cancel)
	* 60 per minute, market quotes
	* 180 per minute, user info like balance, summary, etc

"""
from enum					import Enum
from requests				import Request, Session
from requests.exceptions	import HTTPError,Timeout
from .utils					import (
	pretty_print_POST,
	JSONStreamParser
)
import datetime
import logging








# Global timeout variable
_timeout = 1.0



class RequestType(Enum):
	Order	= 1
	Quote	= 2
	Info	= 3




class Endpoint:
	"""Base abstract module from which all other account endpoints inherit.
	"""

	# Host
	_host = 'https://api.tradeking.com/v1/'
	
	# One of RequestType
	_type = None

	# Extension
	_resource = ''

	# GET, POST, etc.
	_method	= 'GET'

	# results
	_results = None

	req = None
	




	@classmethod
	def url ( cls ):
		return cls._host + cls._resource
	




	@classmethod
	def resolve ( cls, **kwargs):
		"""Can insert account information into the url
		This is just a placeholder
		"""
		return cls.url()






	def extract ( self, response ):
		"""Extract certain fields from response
		"""
		return response.json().get('response')






	def req_body ( self, **kwargs ):
		"""Return get params together with post body data
		"""
		return None, None







	def _fetch_raw ( self, stream=False ):
		return self.s.send(
			self.req,
			stream=stream
		)



	def request ( self=None ):
		"""Execute an entire loop, and aggregate results
		"""
		x = self._fetch_raw()

		x.raise_for_status()

		return self.extract ( x )




	

	def __init__ ( self, auth = None, **kwargs ):
		"""Create and send request
		Return the processed result
		"""

		# Get post and get data
		send_params, send_data = self.req_body (**kwargs)


		# Get the session
		if auth is not None:
			self.s = auth.sess
		else:
			self.s = Session()


		req_auth = None if auth is None else auth.auth
		
		# Create a prepped request
		self.req = self.s.prepare_request(
			Request(
				self._method,
				self.resolve( **kwargs ),
				auth	= req_auth,
				params	= send_params,
				data	= send_data
			)
		)








class AuthenticatedEndpoint ( Endpoint ):
	"""Simple class, just require auth. Non-auth is non-optional
	"""
	def __init__ ( self, auth, **kwargs ):
		"""Create and send request
		Return the processed result
		"""
		super().__init__(auth,**kwargs)







class AccountEndpoint ( AuthenticatedEndpoint ):
	"""Authenticated endpoint + account information
	"""
	def resolve ( self, **kwargs):
		"""Inject the account number into the call
		"""
		return self.url().format(kwargs.get('account_nbr'))






class StreamEndpoint ( AuthenticatedEndpoint ):
	"""Streams an endpoint.
	"""
	_host		= 'https://stream.tradeking.com/v1/'
	def request ( self=None ):
		"""Execute an entire loop, and aggregate results
		"""

		x = self._fetch_raw(stream=True)

		x.raise_for_status()

		p = JSONStreamParser()

		for chunk in x.iter_content( chunk_size=1 ):
			it = p.stream(chunk.decode('utf-8'))
			while True:
				try:
					row = next(it)
				except StopIteration:
					pass
				else:
					quote = row.get('quote')
					if quote is not None:
						yield quote
				finally:
					del it
					break







def setTimeout ( t ):
	"""Sets the global request response timeout variable
	"""
	if t is not None:
		_timeout = float(t)
