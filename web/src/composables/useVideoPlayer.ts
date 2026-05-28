import { onBeforeUnmount, ref, type Ref } from 'vue';
import Hls from 'hls.js';
import Plyr from 'plyr';
import 'plyr/dist/plyr.css';

export interface MountVideoOptions {
  source: string;
  isHls: boolean;
  onFatalError?: (message: string) => void;
}

export function useVideoPlayer(videoRef: Ref<HTMLVideoElement | null>) {
  const isReady = ref(false);
  let hlsPlayer: Hls | null = null;
  let plyrPlayer: Plyr | null = null;

  const destroy = () => {
    if (hlsPlayer) {
      hlsPlayer.destroy();
      hlsPlayer = null;
    }
    if (plyrPlayer) {
      plyrPlayer.destroy();
      plyrPlayer = null;
    }
    const video = videoRef.value;
    if (video) {
      video.removeAttribute('src');
      video.load();
    }
    isReady.value = false;
  };

  const mount = ({ source, isHls, onFatalError }: MountVideoOptions) => {
    const video = videoRef.value;
    if (!video || !source) return;

    destroy();

    if (isHls && Hls.isSupported()) {
      hlsPlayer = new Hls({ enableWorker: true, lowLatencyMode: true });
      hlsPlayer.loadSource(source);
      hlsPlayer.attachMedia(video);
      hlsPlayer.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          onFatalError?.('Unable to play this HLS stream.');
        }
      });
    } else {
      video.src = source;
    }

    plyrPlayer = new Plyr(video, {
      controls: [
        'play-large',
        'play',
        'progress',
        'current-time',
        'mute',
        'volume',
        'settings',
        'pip',
        'fullscreen',
      ],
      settings: ['speed'],
      speed: { selected: 1, options: [0.75, 1, 1.25, 1.5, 2] },
      keyboard: { focused: true, global: false },
    });
    isReady.value = true;
  };

  onBeforeUnmount(destroy);

  return { mount, destroy, isReady };
}
