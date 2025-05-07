import asyncio

from livekit import api
from livekit.protocol.sip import CreateSIPOutboundTrunkRequest, SIPOutboundTrunkInfo

async def main():
  livekit_api = api.LiveKitAPI()

  trunk = SIPOutboundTrunkInfo(
    name = "Pranesh",
    address = "pranesh.pstn.twilio.com",
    numbers = ['+18337801460'],
    auth_username = "pranesh_sip",
    auth_password = "PNKumar41942"
  )

  request = CreateSIPOutboundTrunkRequest(
    trunk = trunk
  )

  trunk = await livekit_api.sip.create_sip_outbound_trunk(request)

  print(f"Successfully created {trunk}")

  await livekit_api.aclose()

asyncio.run(main())